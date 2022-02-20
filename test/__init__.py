class MockDbQuery(object):
    def __init__(self, responses):
        self.responses = responses

    def get(self, method, **kws):
        resp = None
        if method in self.responses:
            resp = self.responses[method].pop(0)

            if 'validate' in resp:
                checks = resp['validate']['checks']
                resp = resp['validate']['data']
                for check in checks:
                    assert check in kws
                    expected_value = checks[check]
                    assert expected_value == kws[check]
        return resp


class MockHTTPResponse(object):
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text
