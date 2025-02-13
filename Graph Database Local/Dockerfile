# Use the official Neo4j image as base
FROM neo4j:5.13.0

# Set environment variables for configuration
ENV NEO4J_AUTH=neo4j/your_password_here
ENV NEO4J_ACCEPT_LICENSE_AGREEMENT=yes

# Expose the necessary ports
# 7474: HTTP
# 7473: HTTPS
# 7687: Bolt
EXPOSE 7474 7473 7687

# Create a volume for data persistence
VOLUME /data

# Set memory configurations (adjust these based on your system)
ENV NEO4J_dbms_memory_heap_initial__size=512m
ENV NEO4J_dbms_memory_heap_max__size=1G
ENV NEO4J_dbms_memory_pagecache_size=512m

# Enable APOC plugin (optional but recommended)
ENV NEO4J_dbms_security_procedures_unrestricted=apoc.*

# Add custom configurations if needed
COPY neo4j.conf /conf/neo4j.conf

# Healthcheck to ensure Neo4j is running
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
  CMD wget http://localhost:7474 -q -O - > /dev/null 2>&1

# Command to run Neo4j
CMD ["neo4j"]