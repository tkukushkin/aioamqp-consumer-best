from aioamqp_consumer_best.records import ConnectionParams


class TestConnectionParams:
    def test_from_string(self):
        assert ConnectionParams.from_string("amqp://user@host//") == ConnectionParams(
            host="host",
            username="user",
        )
