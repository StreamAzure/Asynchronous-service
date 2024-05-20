import json
import re


class Span:
    def __init__(self, span):
        self.traceID = span["traceId"]
        self.segmentID = span["segmentId"]
        self.spanID = span["spanId"]
        self.parentSpanId = span["parentSpanId"]
        self.refs = span["refs"]
        self.service = span["serviceCode"]
        self.startTime = span["startTime"]
        self.endTime = span["endTime"]
        self.endpointName = span["endpointName"]
        self.type = span["type"]
        self.component = span["component"]
        self.isError = span["isError"]
        self.layer = span["layer"]
        self.tags = self._parse_tags(span["tags"])
        self.sqlStmt = self._parse_SQL()
        self.sqlStmt_with_param = self._parse_SQL(params=True)
        self.x_operation_type = ""

    def __hash__(self):
        return hash((self.traceID, self.segmentID, self.spanID, self.x_operation_type))

    def __str__(self):
        """
        返回 span 对象的字符串表示形式
        """
        span_info = {
            "x_operation_type": self.x_operation_type,
            "traceID": self.traceID,
            "segmentID": self.segmentID, 
            "spanID": self.spanID,
            "service": self.service,
            # "startTime": self.startTime,
            # "endTime": self.endTime,
            "endpointName": self.endpointName,
            # "type": self.type,
            "component": self.component,
            # "layer": self.layer,
            "tags": self.tags,
        }
        return json.dumps(span_info, indent=2)

    def _parse_tags(self, tag_list) -> dict:
        """
        解析 tag 字段
        """
        tags = {}
        for tag in tag_list:
            tags[tag['key']] = tag['value']
        return tags
    
    def _parse_SQL(self, params = False):
        pattern = r"Mysql/JDBC/PreparedStatement/(.*)"
        match = re.match(pattern, self.endpointName)
        if match:
            stat = self.tags["db.statement"]
            completed_stat = stat
            if params and "db.sql.parameters" in self.tags.keys():
                exec_tpye = match.group(1)
                params = self.tags["db.sql.parameters"].strip("[]").split(",")
                if exec_tpye == "executeQuery":
                    # where_clause = stat.split("where ")[1]
                    if len(params) > 0:
                        for param in params:
                            completed_stat = completed_stat.replace("?", param, 1)
                elif exec_tpye == "executeUpdate":
                    if len(params) > 0:
                        for param in params:
                            completed_stat = completed_stat.replace("?", param, 1)
            return completed_stat
        else:
            return None

class Req:
    def __init__(self, method, url, body, endpointName, type) -> None:
        self.method = method # 'GET','PUT', etc.
        self.url = url
        self.body = json.loads(body) if body != "" else {}
        self.type = type # 'read' or 'write'
        self.endpointName = endpointName

    def __str__(self) -> str:
        if self.body != "":
            return f"[{self.type}] {self.method} {self.url} {self.body}"
        else:
            return f"[{self.type}] {self.method} {self.url}"
    
    def __dict__(self) -> dict:
        return {
            "type":self.type,
            "url":self.url,
            "body":self.body,
            "method":self.method
        }
    
    def __eq__(self, other):
        if isinstance(other, Req):
            if self.method != other.method or self.url != other.url:
                return False
            if self.endpointName != other.endpointName or self.type != other.type:
                return False
            if self.body != other.body:
                return False
            return True
        return False
    
    def __json__(self):
        return self.__dict__()
    
class Bundle:
    def __init__(self, reqSpan:Span, ids:list) -> None:
        self.reqSpan = reqSpan
        self.ids = ids
    
    def __hash__(self):
        return hash((self.reqSpan, tuple(self.ids)))