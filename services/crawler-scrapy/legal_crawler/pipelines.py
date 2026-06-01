import hashlib
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import boto3
from itemadapter import ItemAdapter


class S3Pipeline:
    def __init__(self):
        self.s3 = None
        if os.getenv("S3_ACCESS_KEY"):
            self.s3 = boto3.client(
                "s3",
                endpoint_url=os.getenv("S3_ENDPOINT"),
                region_name=os.getenv("S3_REGION", "ru-3"),
                aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
            )
        self.bucket = os.getenv("S3_BUCKET", "knowledge-raw")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        url = adapter.get("url", "")
        content = adapter.get("content", "")
        source_id = spider.name

        if self.s3 and content:
            domain = urlparse(url).netloc
            ts = datetime.now(timezone.utc).strftime("%Y/%m/%d")
            key = f"raw/{source_id}/{domain}/{ts}/{hashlib.md5(url.encode()).hexdigest()}.md"
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType="text/markdown",
                Metadata={"source_url": url},
            )
            adapter["storage_path"] = f"s3://{self.bucket}/{key}"
        else:
            local_dir = f"/app/data/{source_id}"
            os.makedirs(local_dir, exist_ok=True)
            path = f"{local_dir}/{hashlib.md5(url.encode()).hexdigest()}.md"
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            adapter["storage_path"] = path

        return item
