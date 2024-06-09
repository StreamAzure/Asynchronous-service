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
        Returns the string representation of the span object
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
        Parses the tag field
        """
        tags = {}
        for tag in tag_list:
            tags[tag['key']] = tag['value']
        return tags
    
    def _parse_SQL(self, params=False):
        pattern = r"Mysql/JDBC/PreparedStatement/(.*)"
        match = re.match(pattern, self.endpointName)
        if match:
            stat = self.tags["db.statement"]
            completed_stat = stat
            if params and "db.sql.parameters" in self.tags.keys():
                exec_type = match.group(1)
                params = self.tags["db.sql.parameters"].strip("[]").split(",")
                if exec_type == "executeQuery":
                    # where_clause = stat.split("where ")[1]
                    if len(params) > 0:
                        for param in params:
                            completed_stat = completed_stat.replace("?", param, 1)
                elif exec_type == "executeUpdate":
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
        self.db_infos = [] # Database instances and database names affected along the request flow path

    def have_child_flow(self):
        return len(self.child_flow_ids) != 0
    
    def get_original_requestSpan(self):
        """
        Gets the original user request's RequestSpan
        """
        return self.requestSpans[0]
    
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
    def __init__(self, flowID, flowSpanID, span):
        self.flowID = flowID # Belonging request flow
        self.flowSpanID = flowSpanID # The nth span in the request flow
        self.span = span
        self.corresponding_entrySpan_unique_id = ""
        self.sqls = []

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
        self.operation = self._get_operation(self.span) # 'write' or 'read'
        self.db_operation = self._get_db_operation(self.span) # Database operation type
        self.ids = self._get_ids(self.span) # Suspected primary key values involved
        self.peer = span.peer
        self.db = span.tags["db.instance"]
    
    def _get_db_operation(self, span):
        """
        Gets the database operation type
        """
        stmt = span.sqlStmt
        if stmt is None:
            raise Exception(f"DataSpan {span.segmentID + '-' + str(span.spanID)} is not a valid SQL span!")
        return get_operation(stmt).lower()
    
    def _get_operation(self, span):
        """
        Returns 'read' if the operation is SELECT
        Otherwise returns 'write'
        """
        if self._get_db_operation(span) == 'select':
            return 'read'
        else:
            return 'write'
    
    def _get_ids(self, span):
        if span.sqlStmt is None:
            raise Exception(f"DataSpan {span.segmentID + '-' + str(span.spanID)} is not a valid SQL span!")
        
        KEYWORDS = ["id", "ID", "Id"]

        fields, _ = get_sql_keys(span.sqlStmt)
        values = []
        if "db.sql.parameters" in span.tags.keys():
            values = span.tags["db.sql.parameters"].strip("[]").split(",") # SQL field values
        
        # Bind field names and values
        if get_operation(span.sqlStmt) == 'insert':
            # For insert, the fields in the SQL statement are directly a list, use it directly
            data_dict = dict(zip(fields, values))
        else:
            # For other SQL statements, filter out tokens containing ?, such as document_type=?
            fields = [field for field in fields if "?" in field]
            data_dict = dict(zip(fields, values))

        ids = []
        
        # Heuristically identify the ID fields and find the corresponding values
        # Record spans containing ID values
        for field, value in data_dict.items():
            if any(keyword in field for keyword in KEYWORDS): # Field name contains keywords
                ids.append(value) # Record value

        return ids
