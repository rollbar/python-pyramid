import opentracing

# Ported from the Django library:
# https://github.com/opentracing-contrib/python-django
class PyramidTracer(object):
    '''
    @param tracer the OpenTracing tracer to be used
    to trace requests using this PyramidTracer
    '''
    def __init__(self, tracer, trace_all=False):
        self._tracer = tracer
        self._trace_all = trace_all
        self._current_spans = {}

    def get_span(self, request):
        '''
        @param request 
        Returns the span tracing this request
        '''
        return self._current_spans.get(request, None)

    def trace(self, *attributes):
        '''
        Function decorator that traces functions
        '''
        def decorator(view_func):
            if self._trace_all:
                return view_func

            # otherwise, execute the decorator
            def wrapper(request):
                span = self._apply_tracing(request, list(attributes))
                r = view_func(request)
                self._finish_tracing(request)
                return r

            return wrapper
        return decorator

    def _apply_tracing(self, request, attributes):
        '''
        Helper function to avoid rewriting for middleware and decorator.
        Returns a new span from the request with logged attributes and 
        correct operation name from the view_func.
        '''
        headers = request.headers

        # start new span from trace info
        span = None
        operation_name = request.path # (xxx) fix this thing
        try:
            span_ctx = self._tracer.extract(opentracing.Format.HTTP_HEADERS, headers)
            span = self._tracer.start_span(operation_name=operation_name, child_of=span_ctx)
        except (opentracing.InvalidCarrierException, opentracing.SpanContextCorruptedException) as e:
            span = self._tracer.start_span(operation_name=operation_name)
        if span is None:
            span = self._tracer.start_span(operation_name=operation_name)

        # add span to current spans 
        self._current_spans[request] = span

        # log any traced attributes
        for attr in attributes:
            if hasattr(request, attr):
                payload = str(getattr(request, attr))
                if payload:
                    span.set_tag(attr, payload)
        
        return span

    def _finish_tracing(self, request):
        span = self._current_spans.pop(request, None)     
        if span is not None:
            span.finish()
