import json
import re
from utils.sql_parse import *

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
        self.peer = span["peer"]
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
        
class Flow:
    def __init__(self, id):
        self.id = id
        self.requestSpans = []
        self.child_flow_ids = []
    
    def __str__(self):
        result = ""
        for i, reqSpan in enumerate(self.requestSpans):
            http_str = f"[{reqSpan.span.tags['http.method']}] {reqSpan.span.tags['url']}"
            # http_str = f"{reqSpan.span.endpointName}"
            if i == 0:
                result += f"{http_str}"
            else:
                result += f" -> {http_str}"
        return result

class RequestSpan:
    def __init__(self, flowID, span):
        self.flowID = flowID # 所属请求流
        self.span = span
        self.corresponding_entrySpan_unique_id = ""

    def __eq__(self, other):
        if isinstance(other, RequestSpan):
            unique_id = self.span.segmentID + '-' + str(self.span.spanID)
            other_unique_id = other.span.segmentID + '-' + str(other.span.spanID)
            if self.flowID == other.flowID and unique_id == other_unique_id:
                return True
        return False
    
    def __hash__(self):
        unique_id = self.span.segmentID + '-' + str(self.span.spanID)
        return hash((self.flowID, unique_id))

class DataSpan:
    def __init__(self, span):
        self.span = span
        self.operation = self._get_opertaion(self.span)
        self.ids = self._get_ids(self.span) # 涉及的疑似主键值
        self.peer = span.peer
        self.db = span.tags["db.instance"]
    
    def _get_opertaion(self, span):
        """
        如果为 SELECT，返回 read
        否则返回 write
        """
        stmt = span.sqlStmt
        if stmt is None:
            raise Exception(f"DataSpan {span.segmentID + '-' + str(span.spanID)}  is not a valid SQL span!")
        if get_operation(stmt).lower() == 'select':
            return 'read'
        else:
            return 'write'
    
    def _get_ids(self, span):
        if span.sqlStmt is None :
            raise Exception(f"DataSpan {span.segmentID + '-' + str(span.spanID)} is not a valid SQL span!")
        
        KEYWORDS = ["id", "ID", "Id"]

        fields, _ = get_sql_keys(span.sqlStmt)
        values = []
        if "db.sql.parameters" in span.tags.keys():
            values = span.tags["db.sql.parameters"].strip("[]").split(",") # SQL字段值
        
        # 还无法解析的：
        # SELECT * from route where id in (d693a2c5-ef87-4a3c-bef8-600b43f62c68, 1367db1f-461e-4ab7-87ad-2bcc05fd9cb7, 9fc9c261-3263-4bfa-82f8-bb44e06b2f52, 20eb7122-3a11-423f-b10a-be0dc5bce7db, 0b23bd3e-876a-4af3-b920-c50a90c90b04)

        # 捆绑字段名和值
        if get_operation(span.sqlStmt) == 'insert':
            # 对于 insert，SQL语句中 fields 直接为一个列表，直接使用
            data_dict = dict(zip(fields, values))
        else:
            # 对于其他SQL语句，筛选含有 ? 的token，如 document_type=?
            fields = [field for field in fields if "?" in field]
            data_dict = dict(zip(fields, values))

        ids = []
        
        # 启发式识别其中的ID字段，并找到对应值
        # 记录含有ID值的span
        for field, value in data_dict.items():
            if any(keyword in field for keyword in KEYWORDS): # 字段名中包含关键字
                ids.append(value) # 记录值

        return ids