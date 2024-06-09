FROM openjdk:8-jre

RUN /bin/cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone

ADD ./target/ts-basic-service-1.0.jar /app/
ADD ./apache-skywalking-java-agent-9.2.0.tgz /app/

ENV SW_AGENT_NAME=ts-basic-service
ENV SW_AGENT_COLLECTOR_BACKEND_SERVICES=oap-server:11800
# 捕获的数据库语句显示具体参数
ENV SW_JDBC_TRACE_SQL_PARAMETERS=true
ENV JAVA_TOOL_OPTIONS "-javaagent:/app/skywalking-agent/skywalking-agent.jar"
CMD ["java", "-Xmx200m",  "-jar", "/app/ts-basic-service-1.0.jar"]

EXPOSE 15680