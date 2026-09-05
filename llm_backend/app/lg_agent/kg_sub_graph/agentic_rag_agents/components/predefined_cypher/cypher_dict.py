from typing import Dict

predefined_cypher_dict: Dict[str, str] = {
    # Product queries
    "product_by_name": "MATCH (p:Product)-[:BELONGS_TO]->(c:Category) WHERE toLower(p.ProductName) CONTAINS toLower($product_name) RETURN p.ProductName, p.UnitPrice, p.UnitsInStock, c.CategoryName ORDER BY p.ProductName",
    "product_by_category": "MATCH (p:Product)-[:BELONGS_TO]->(c:Category) WHERE toLower(c.CategoryName) = toLower($category_name) RETURN p.ProductName, p.UnitPrice, p.UnitsInStock ORDER BY p.ProductName",
    "product_by_supplier": "MATCH (p:Product)-[:SUPPLIED_BY]->(s:Supplier) WHERE toLower(s.CompanyName) = toLower($supplier_name) RETURN p.ProductName, p.UnitPrice, p.UnitsInStock ORDER BY p.ProductName",
    "products_low_stock": "MATCH (p:Product)-[:BELONGS_TO]->(c:Category) WHERE toInteger(p.UnitsInStock) < toInteger($stock_threshold) RETURN p.ProductName, p.UnitsInStock, c.CategoryName ORDER BY toInteger(p.UnitsInStock)",
    "products_in_stock": "MATCH (p:Product)-[:BELONGS_TO]->(c:Category) WHERE toInteger(p.UnitsInStock) > 0 RETURN p.ProductName, p.UnitPrice, p.UnitsInStock, c.CategoryName ORDER BY p.ProductName",
    "products_out_of_stock": "MATCH (p:Product)-[:BELONGS_TO]->(c:Category) WHERE toInteger(p.UnitsInStock) = 0 RETURN p.ProductName, p.UnitPrice, c.CategoryName ORDER BY p.ProductName",
    "products_by_price_range": "MATCH (p:Product)-[:BELONGS_TO]->(c:Category) WHERE toFloat(p.UnitPrice) >= toFloat($min_price) AND toFloat(p.UnitPrice) <= toFloat($max_price) RETURN p.ProductName, p.UnitPrice, p.UnitsInStock, c.CategoryName ORDER BY toFloat(p.UnitPrice)",
    
    # Customer queries
    "customer_by_name": "MATCH (c:Customer) WHERE toLower(c.CompanyName) CONTAINS toLower($customer_name) RETURN c.CompanyName, c.ContactName, c.Phone, c.Country ORDER BY c.CompanyName",
    "customer_orders": "MATCH (c:Customer)-[:PLACED]->(o:Order) WHERE toLower(c.CompanyName) = toLower($customer_name) RETURN o.orderId, o.OrderDate, o.RequiredDate, o.ShippedDate ORDER BY o.OrderDate DESC",
    "customer_purchase_history": "MATCH (c:Customer)-[:PLACED]->(o:Order)-[contains:CONTAINS]->(p:Product) WHERE toLower(c.CompanyName) = toLower($customer_name) RETURN p.ProductName, o.OrderDate, contains.Quantity, contains.UnitPrice ORDER BY o.OrderDate DESC",
    "customers_by_country": "MATCH (c:Customer) WHERE toLower(c.Country) = toLower($country) RETURN c.CompanyName, c.ContactName, c.Phone, c.Country ORDER BY c.CompanyName",
    
    # Order queries
    "order_by_id": "MATCH (o:Order) WHERE toString(o.orderId) = toString($order_id) RETURN o.orderId, o.OrderDate, o.RequiredDate, o.ShippedDate, o.CustomerName",
    "order_details": "MATCH (o:Order)-[contains:CONTAINS]->(p:Product) WHERE toString(o.orderId) = toString($order_id) RETURN p.ProductName, contains.Quantity, contains.UnitPrice, toFloat(contains.Quantity) * toFloat(contains.UnitPrice) AS TotalPrice ORDER BY p.ProductName",
    "recent_orders": "MATCH (o:Order) RETURN o.orderId, o.OrderDate, o.CustomerName ORDER BY o.OrderDate DESC LIMIT 10",
    "delayed_orders": "MATCH (o:Order) WHERE o.RequiredDate < o.ShippedDate OR (o.RequiredDate < date() AND o.ShippedDate IS NULL) RETURN o.orderId, o.OrderDate, o.RequiredDate, o.ShippedDate, o.CustomerName ORDER BY o.RequiredDate",
    "orders_by_customer": "MATCH (c:Customer)-[:PLACED]->(o:Order) WHERE toLower(c.CompanyName) = toLower($customer_name) RETURN o.orderId, o.OrderDate, o.RequiredDate, o.ShippedDate ORDER BY o.OrderDate DESC",
    "orders_by_date_range": "MATCH (o:Order) WHERE date(o.OrderDate) >= date($start_date) AND date(o.OrderDate) <= date($end_date) RETURN o.orderId, o.OrderDate, o.CustomerName, o.ShippedDate ORDER BY o.OrderDate",
    
    # Supplier queries
    "supplier_by_name": "MATCH (s:Supplier) WHERE toLower(s.CompanyName) CONTAINS toLower($supplier_name) RETURN s.CompanyName, s.ContactName, s.Phone, s.Country ORDER BY s.CompanyName",
    "supplier_by_country": "MATCH (s:Supplier) WHERE toLower(s.Country) = toLower($country) RETURN s.CompanyName, s.ContactName, s.Phone ORDER BY s.CompanyName",
    "supplier_products": "MATCH (s:Supplier)<-[:SUPPLIED_BY]-(p:Product) WHERE toLower(s.CompanyName) = toLower($supplier_name) RETURN p.ProductName, p.UnitPrice, p.UnitsInStock ORDER BY p.ProductName",
    
    # Category queries
    "all_categories": "MATCH (c:Category) RETURN c.CategoryName, c.Description ORDER BY c.CategoryName",
    "category_product_count": "MATCH (c:Category)<-[:BELONGS_TO]-(p:Product) RETURN c.CategoryName, count(p) AS ProductCount ORDER BY ProductCount DESC",
    "categories_with_low_stock_products": "MATCH (c:Category)<-[:BELONGS_TO]-(p:Product) WHERE toInteger(p.UnitsInStock) < toInteger($stock_threshold) RETURN c.CategoryName, count(p) AS LowStockProductCount ORDER BY LowStockProductCount DESC",
    
    # Employee queries
    "employee_by_name": "MATCH (e:Employee) WHERE toLower(e.FirstName + ' ' + e.LastName) CONTAINS toLower($employee_name) RETURN e.FirstName, e.LastName, e.Title, e.HireDate ORDER BY e.LastName, e.FirstName",
    "employee_processed_orders": "MATCH (e:Employee)-[:PROCESSED]->(o:Order) WHERE toLower(e.FirstName + ' ' + e.LastName) = toLower($employee_name) RETURN o.orderId, o.OrderDate, o.CustomerName ORDER BY o.OrderDate DESC",
    # "employee_order_count": "MATCH (e:Employee)-[:PROCESSED]->(o:Order) RETURN e.FirstName, e.LastName, count(o) AS OrderCount ORDER BY OrderCount DESC",
    
    # Shipper queries
    "all_shippers": "MATCH (s:Shipper) RETURN s.CompanyName, s.Phone ORDER BY s.CompanyName",
    "orders_by_shipper": "MATCH (o:Order)-[:SHIPPED_VIA]->(s:Shipper) WHERE toLower(s.CompanyName) = toLower($shipper_name) RETURN o.orderId, o.OrderDate, o.ShippedDate, o.CustomerName ORDER BY o.OrderDate DESC",
    "shipper_order_count": "MATCH (o:Order)-[:SHIPPED_VIA]->(s:Shipper) RETURN s.CompanyName, count(o) AS OrderCount ORDER BY OrderCount DESC",
    
    # Sales analysis queries
    "product_sales": "MATCH (o:Order)-[contains:CONTAINS]->(p:Product) WHERE toLower(p.ProductName) = toLower($product_name) RETURN p.ProductName, sum(toFloat(contains.Quantity) * toFloat(contains.UnitPrice)) AS TotalSales",
    "category_sales": "MATCH (o:Order)-[contains:CONTAINS]->(p:Product)-[:BELONGS_TO]->(c:Category) RETURN c.CategoryName, sum(toFloat(contains.Quantity) * toFloat(contains.UnitPrice)) AS TotalSales ORDER BY TotalSales DESC",
    "supplier_sales": "MATCH (o:Order)-[contains:CONTAINS]->(p:Product)-[:SUPPLIED_BY]->(s:Supplier) RETURN s.CompanyName, sum(toFloat(contains.Quantity) * toFloat(contains.UnitPrice)) AS TotalSales ORDER BY TotalSales DESC",
    "monthly_sales": "MATCH (o:Order)-[contains:CONTAINS]->(p:Product) RETURN substring(toString(o.OrderDate), 0, 7) AS Month, sum(toFloat(contains.Quantity) * toFloat(contains.UnitPrice)) AS Sales ORDER BY Month",
    "top_selling_products": "MATCH (o:Order)-[contains:CONTAINS]->(p:Product) RETURN p.ProductName, sum(toFloat(contains.Quantity)) AS TotalQuantity, sum(toFloat(contains.Quantity) * toFloat(contains.UnitPrice)) AS TotalSales ORDER BY TotalSales DESC LIMIT 10",
    
    # Smart home product queries
    "smart_home_products": "MATCH (p:Product)-[:BELONGS_TO]->(c:Category) WHERE toLower(c.CategoryName) CONTAINS 'smart' RETURN p.ProductName, p.UnitPrice, p.UnitsInStock, c.CategoryName ORDER BY c.CategoryName, p.ProductName",
    "smart_home_products_by_category": "MATCH (p:Product)-[:BELONGS_TO]->(c:Category) WHERE toLower(c.CategoryName) = toLower($category_name) RETURN p.ProductName, p.UnitPrice, p.UnitsInStock, c.CategoryName ORDER BY p.ProductName",
    "smart_home_products_in_stock": "MATCH (p:Product)-[:BELONGS_TO]->(c:Category) WHERE toLower(c.CategoryName) CONTAINS 'smart' AND toInteger(p.UnitsInStock) > 0 RETURN p.ProductName, p.UnitPrice, p.UnitsInStock, c.CategoryName ORDER BY c.CategoryName, p.ProductName"
}