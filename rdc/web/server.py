from rdc.dic import Container as BaseContainer

class Container(BaseContainer):
    @staticmethod
    def configure(self, *args, **kwargs):
        """Depencency injection container configurator."""
        prefix = kwargs.pop('prefix', __name__ if '__name__' in locals() else 'rdc.web')
        p = lambda name: '.'.join((prefix, name, ))
        r = lambda name: self.ref(p(name[1:]) if name[0] is '.' else name)

        server_kwargs = {
            'hostname': kwargs.pop('bind', None) or r('.server.bind'),
            'port': kwargs.pop('port', None) or r('.server.port'),
            'use_debugger': kwargs.pop('debug', None) or r('.server.debug'),
            'use_reloader': kwargs.pop('reload', None) or r('.server.reload'),
        }
        if 'application' in kwargs:
            server_kwargs['application'] = kwargs['application']

        #
        # Embedded development web server
        #
        @self.definition(prefix, **server_kwargs)
        def server(**kwargs):
            try:
                from werkzeug.serving import run_simple
            except ImportError as e:
                raise ImportError(
                    'You must install werkzeug to use the embedded development webserver (try "pip install werkzeug").'
                )

            def server(*lastminute_args, **lastminute_kwargs):
                kwargs.update(lastminute_kwargs)
                return run_simple(**kwargs)

            return server
