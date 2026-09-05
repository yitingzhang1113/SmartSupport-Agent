#!/usr/bin/env bash
set -euo pipefail

"/opt/neo4j/bin/neo4j-admin" database import full neo4j --overwrite-destination=true \
  --nodes=Product="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/product_nodes.csv" \
  --nodes=Category="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/category_nodes.csv" \
  --nodes=Supplier="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/supplier_nodes.csv" \
  --nodes=Customer="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/customer_nodes.csv" \
  --nodes=Employee="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/employee_nodes.csv" \
  --nodes=Shipper="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/shipper_nodes.csv" \
  --nodes=Order="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/order_nodes.csv" \
  --nodes=Review="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/review_nodes.csv" \
  --relationships=BELONGS_TO="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/product_category_edges.csv" \
  --relationships=SUPPLIED_BY="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/product_supplier_edges.csv" \
  --relationships=PLACED="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/customer_order_edges.csv" \
  --relationships=PROCESSED="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/employee_order_edges.csv" \
  --relationships=SHIPPED_VIA="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/order_shipper_edges.csv" \
  --relationships=CONTAINS="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/order_product_edges.csv" \
  --relationships=REPORTS_TO="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/employee_reports_to_edges.csv" \
  --relationships=WROTE="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/customer_review_edges.csv" \
  --relationships=ABOUT="/home/anna/projects/AI_agent/Intel_Customer_Ser/SmartSupport_agent/llm_backend/app/graphrag/origin_data/output_data/data/neo4j_admin/review_product_edges.csv" \
  --delimiter="," \
  --array-delimiter=";" \
--multiline-fields=true \
--skip-bad-relationships=true \
--skip-duplicate-nodes=true
