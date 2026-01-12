"""
API 集成测试
"""
import pytest
import time
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    # 使用正确的方式初始化 TestClient
    with TestClient(app) as c:
        yield c


class TestDocumentAPI:
    """文档 API 测试套件"""

    def test_upload_document(self, client):
        """测试文档上传"""
        with open("tests/fixtures/sample.pdf", "rb") as f:
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        assert response.status_code == 200
        data = response.json()
        assert "doc_id" in data
        assert data["status"] == "processing"

        return data["doc_id"]

    def test_upload_invalid_format(self, client):
        """测试上传不支持的格式"""
        # 创建临时文本文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            with open(temp_path, "rb") as f:
                response = client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("sample.txt", f, "text/plain")}
                )

            assert response.status_code == 400
        finally:
            import os
            os.unlink(temp_path)

    def test_list_documents(self, client):
        """测试文档列表"""
        response = client.get("/api/v1/documents/list")

        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert isinstance(data["documents"], list)

    def test_upload_and_process(self, client):
        """测试上传和处理完整流程"""
        pdf_file = "tests/fixtures/sample.pdf"

        if not Path(pdf_file).exists():
            pytest.skip(f"测试文件不存在: {pdf_file}")

        # 1. 上传文档
        with open(pdf_file, "rb") as f:
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        assert response.status_code == 200
        doc_id = response.json()["doc_id"]

        # 2. 等待处理完成（最多 60 秒）
        max_wait = 60
        start = time.time()

        while time.time() - start < max_wait:
            response = client.get(f"/api/v1/documents/{doc_id}")

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ready":
                    break

            time.sleep(2)

        # 3. 验证最终结果
        final_response = client.get(f"/api/v1/documents/{doc_id}")
        assert final_response.status_code == 200
        data = final_response.json()

        assert "content" in data
        assert len(data["content"]) > 0
        assert "images" in data
        assert isinstance(data["images"], list)

    def test_get_nonexistent_document(self, client):
        """测试获取不存在的文档"""
        response = client.get("/api/v1/documents/nonexistent-id")
        assert response.status_code == 404

    def test_health_ping(self, client):
        """测试健康检查 ping"""
        response = client.get("/api/v1/health/ping")
        assert response.status_code == 200
        assert response.json()["status"] == "pong"

    def test_get_image_nonexistent(self, client):
        """测试获取不存在的图像"""
        response = client.get("/api/v1/documents/fake-doc/images/img_001")
        assert response.status_code == 404
