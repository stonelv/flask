import logging
import json
from flask import Flask
from flask.request_logger import RequestLogger


def test_request_logger_disabled():
    """测试禁用RequestLogger的情况。"""
    app = Flask(__name__)
    app.config['REQUEST_LOGGER_ENABLED'] = False
    
    logger = RequestLogger(app)
    
    @app.route('/')
    def index():
        return 'Hello, World!'
    
    client = app.test_client()
    response = client.get('/')
    
    # 验证响应头中没有X-Request-ID
    assert 'X-Request-ID' not in response.headers
    
    # 验证响应内容正确
    assert response.data == b'Hello, World!'


def test_request_logger_header_injection():
    """测试RequestLogger是否正确注入X-Request-ID响应头。"""
    app = Flask(__name__)
    
    logger = RequestLogger(app)
    
    @app.route('/')
    def index():
        return 'Hello, World!'
    
    client = app.test_client()
    response = client.get('/')
    
    # 验证响应头中包含X-Request-ID
    assert 'X-Request-ID' in response.headers
    
    # 验证Request ID格式是否为UUIDv4
    request_id = response.headers['X-Request-ID']
    assert len(request_id) == 36
    assert request_id[8] == '-' and request_id[13] == '-' and request_id[18] == '-' and request_id[23] == '-'
    
    # 验证响应内容正确
    assert response.data == b'Hello, World!'


def test_request_logger_custom_header():
    """测试自定义Request ID响应头名称。"""
    app = Flask(__name__)
    app.config['REQUEST_LOGGER_HEADER_NAME'] = 'X-Custom-Request-ID'
    
    logger = RequestLogger(app)
    
    @app.route('/')
    def index():
        return 'Hello, World!'
    
    client = app.test_client()
    response = client.get('/')
    
    # 验证响应头中包含自定义的Request ID头
    assert 'X-Custom-Request-ID' in response.headers
    assert 'X-Request-ID' not in response.headers


def test_request_logger_json_logging(caplog):
    """测试JSON格式的日志记录。"""
    app = Flask(__name__)
    app.config['REQUEST_LOGGER_LOG_JSON'] = True
    
    logger = RequestLogger(app)
    
    @app.route('/')
    def index():
        return 'Hello, World!'
    
    # 设置日志级别
    caplog.set_level(logging.INFO)
    
    client = app.test_client()
    response = client.get('/')
    
    # 验证日志是否被记录
    assert len(caplog.records) == 1
    
    # 验证日志消息是否正确
    log_record = caplog.records[0]
    assert log_record.message == 'Request completed'


def test_request_logger_non_json_logging(caplog):
    """测试非JSON格式的日志记录。"""
    app = Flask(__name__)
    app.config['REQUEST_LOGGER_LOG_JSON'] = False
    
    logger = RequestLogger(app)
    
    @app.route('/')
    def index():
        return 'Hello, World!'
    
    # 设置日志级别
    caplog.set_level(logging.INFO)
    
    client = app.test_client()
    response = client.get('/')
    
    # 验证日志是否被记录
    assert len(caplog.records) == 1
    
    # 验证日志消息是否正确
    log_record = caplog.records[0]
    assert log_record.message == 'Request completed'


def test_request_logger_log_level(caplog):
    """测试不同日志级别的设置。"""
    # 测试DEBUG级别
    app1 = Flask(__name__)
    app1.config['REQUEST_LOGGER_LOG_LEVEL'] = 'DEBUG'
    
    logger1 = RequestLogger(app1)
    
    @app1.route('/')
    def index1():
        return 'Hello, World!'
    
    # 设置捕获的日志级别为DEBUG
    caplog.set_level(logging.DEBUG)
    
    client1 = app1.test_client()
    client1.get('/')
    
    # 验证日志是否被记录
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == 'INFO'
    
    # 测试WARNING级别
    app2 = Flask(__name__)
    app2.config['REQUEST_LOGGER_LOG_LEVEL'] = 'WARNING'
    
    logger2 = RequestLogger(app2)
    
    @app2.route('/')
    def index2():
        return 'Hello, World!'
    
    caplog.clear()
    client2 = app2.test_client()
    client2.get('/')
    
    # 验证日志是否没有被记录（因为级别不够）
    assert len(caplog.records) == 0
