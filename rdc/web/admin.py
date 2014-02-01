# -*- coding: utf-8 -*-
#
# Copyright 2012-2014 Romain Dorgueil
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from functools import partial
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.util import has_identity
from webapp2 import cached_property, abort, RequestHandler as _RequestHandler
from wtforms.ext.sqlalchemy.orm import model_form
from rdc.web.paginator import Paginator

class View(object):
    Model = None
    route_prefix = None
    columns = ['__unicode__']
    labels = {
        '__unicode__': 'Object'
    }

    def __init__(self, **kwargs):
        self.route_prefix = kwargs.get('route_prefix', None) or self.route_prefix

    def route_for(self, action):
        if action == 'list' or action is None:
            return self.route_prefix
        return '.'.join((self.route_prefix, action, ))

    def render(self, object, column):
        renderer_name = 'render_{0}'.format(column)
        if hasattr(self, renderer_name):
            return getattr(self, renderer_name)(object)
        v = getattr(object, column)
        if callable(v):
            return v()
        return v

    def get_columns(self):
        return self.columns

    def get_label_for(self, column):
        return self.labels[column] if column in self.labels else column.capitalize()

def ModelView(model, route_prefix):
    cls = type(model.__name__+'View', (View, ), {})
    cls.Model = model
    cls.route_prefix = route_prefix
    return cls

class ListView(View):
    Paginator = partial(Paginator, per_page=20)
    actions = ['edit', 'delete']

    def __init__(self, *args, **kwargs):
        self.query = kwargs.pop('query')
        self.page = kwargs.pop('page', None)
        self.actions = kwargs.pop('actions', self.actions)

        if self.page:
            self.paginator = self.Paginator(self.query)
        else:
            self.paginator = None

        super(ListView, self).__init__(*args, **kwargs)

    def get_page(self):
        if self.paginator:
            return self.paginator.page(self.page)
        raise RuntimeError('no paginator')

    def objects(self):
        if self.paginator:
            return self.get_page().object_list
        return self.query.all()

    def __len__(self):
        return len(self.objects())

class EditView(View):
    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop('session')
        self.id = kwargs.pop('id', None)

        self.form = None

        print self.session, self.id

    def query_for_id(self, id):
        return self.session.query(self.Model).filter(self.Model.id == id)

    def find(self, id):
        return self.query_for_id(id).one()

    @property
    def query(self):
        return self.query_for_id(self.id)

    @cached_property
    def object(self):
        if self.id:
            try:
                return self.query.one()
            except NoResultFound as e:
                return abort(404)

        return self.Model()

    @cached_property
    def Form(self):
        return model_form(self.Model, self.session, only=self.columns)

    def pre_commit(self):
        return True

    def commit(self):
        self.session.flush()
        self.session.commit()
        return True

    def post_commit(self):
        pass

    def submit(self, request, **kwargs):
        self.form = self.Form(request.POST, self.object)

        if request.method == 'POST':
            if self.form.validate():
                self.form.populate_obj(self.object)
                if self.pre_commit():
                    _retval = self.commit()
                self.post_commit()
                return _retval

    def object_exists(self):
        return has_identity(self.object)

def AdminHandler(ListView, EditView, BaseView, RequestHandler=None):
    RequestHandler = RequestHandler or _RequestHandler

    cls = type(BaseView.Model.__name__+'AdminHandler', (RequestHandler, BaseView, ), {})
    cls.ListView = ListView
    cls.EditView = EditView

    return cls

