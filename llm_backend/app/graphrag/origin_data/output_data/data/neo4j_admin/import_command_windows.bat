@echo off
setlocal

"D:\downloads\neo4j-community-2026.05.0\bin\neo4j-admin.bat" database import full neo4j --overwrite-destination=true ^
  --nodes=Product="D:\smart_support_neo4j_import\product_nodes.csv" ^
  --nodes=Category="D:\smart_support_neo4j_import\category_nodes.csv" ^
  --nodes=Supplier="D:\smart_support_neo4j_import\supplier_nodes.csv" ^
  --nodes=Customer="D:\smart_support_neo4j_import\customer_nodes.csv" ^
  --nodes=Employee="D:\smart_support_neo4j_import\employee_nodes.csv" ^
  --nodes=Shipper="D:\smart_support_neo4j_import\shipper_nodes.csv" ^
  --nodes=Order="D:\smart_support_neo4j_import\order_nodes.csv" ^
  --nodes=Review="D:\smart_support_neo4j_import\review_nodes.csv" ^
  --relationships=BELONGS_TO="D:\smart_support_neo4j_import\product_category_edges.csv" ^
  --relationships=SUPPLIED_BY="D:\smart_support_neo4j_import\product_supplier_edges.csv" ^
  --relationships=PLACED="D:\smart_support_neo4j_import\customer_order_edges.csv" ^
  --relationships=PROCESSED="D:\smart_support_neo4j_import\employee_order_edges.csv" ^
  --relationships=SHIPPED_VIA="D:\smart_support_neo4j_import\order_shipper_edges.csv" ^
  --relationships=CONTAINS="D:\smart_support_neo4j_import\order_product_edges.csv" ^
  --relationships=REPORTS_TO="D:\smart_support_neo4j_import\employee_reports_to_edges.csv" ^
  --relationships=WROTE="D:\smart_support_neo4j_import\customer_review_edges.csv" ^
  --relationships=ABOUT="D:\smart_support_neo4j_import\review_product_edges.csv" ^
  --delimiter="," ^
  --array-delimiter=";" ^
--multiline-fields=true ^
--skip-bad-relationships=true ^
--skip-duplicate-nodes=true

if errorlevel 1 (
  echo Neo4j import failed.
  pause
  exit /b 1
)

echo Neo4j import completed successfully.
pause
endlocal
