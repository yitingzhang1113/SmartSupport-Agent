"""
把 Business_data/ 下的 Northwind CSV 导入 Neo4j,schema 与
app/lg_agent/kg_sub_graph/.../predefined_cypher/cypher_dict.py 中预定义 Cypher 保持一致。

节点: Product / Category / Supplier / Customer / Employee / Shipper / Order / Review
关系:
  (Product)-[:BELONGS_TO]->(Category)          via Product.CategoryID
  (Product)-[:SUPPLIED_BY]->(Supplier)         via Product.SupplierID
  (Customer)-[:PLACED]->(Order)                via Order.CustomerID
  (Employee)-[:PROCESSED]->(Order)             via Order.EmployeeID
  (Order)-[:SHIPPED_VIA]->(Shipper)            via Order.ShipVia
  (Order)-[:CONTAINS {Quantity,UnitPrice,Discount}]->(Product)  via _Order_Details
  (Employee)-[:REPORTS_TO]->(Employee)         via Employee.ReportsTo
  (Customer)-[:WROTE]->(Review)                via Review.CustomerID
  (Review)-[:ABOUT]->(Product)                 via Review.ProductID

注意: Order 节点的主键属性名是小写 orderId (预定义 Cypher 里用 o.orderId)。
"""
import csv
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from app.core.config import settings

ROOT = Path(__file__).parent.parent.parent
DATA = ROOT / "Business_data"


def read_csv(name):
    with open(DATA / name, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    driver = GraphDatabase.driver(
        settings.NEO4J_URL,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
    )
    with driver.session(database=settings.NEO4J_DATABASE) as s:
        print("清空旧数据 ...")
        s.run("MATCH (n) DETACH DELETE n")

        print("建约束/索引 ...")
        for label, key in [
            ("Product", "ProductID"), ("Category", "CategoryID"),
            ("Supplier", "SupplierID"), ("Customer", "CustomerID"),
            ("Employee", "EmployeeID"), ("Shipper", "ShipperID"),
            ("Order", "orderId"), ("Review", "ReviewID"),
        ]:
            s.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{key} IS UNIQUE")

        # ---------- 节点 ----------
        print("导入 Category ...")
        s.run("""
        UNWIND $rows AS r
        MERGE (c:Category {CategoryID: r.CategoryID})
        SET c.CategoryName = r.CategoryName, c.Description = r.Description
        """, rows=read_csv("Categories.csv"))

        print("导入 Supplier ...")
        s.run("""
        UNWIND $rows AS r
        MERGE (x:Supplier {SupplierID: r.SupplierID})
        SET x.CompanyName=r.CompanyName, x.ContactName=r.ContactName,
            x.ContactTitle=r.ContactTitle, x.City=r.City, x.Country=r.Country,
            x.Phone=r.Phone
        """, rows=read_csv("Suppliers.csv"))

        print("导入 Product ...")
        s.run("""
        UNWIND $rows AS r
        MERGE (p:Product {ProductID: r.ProductID})
        SET p.ProductName=r.ProductName, p.SupplierID=r.SupplierID,
            p.CategoryID=r.CategoryID, p.QuantityPerUnit=r.QuantityPerUnit,
            p.UnitPrice=toFloat(r.UnitPrice), p.UnitsInStock=toInteger(r.UnitsInStock),
            p.UnitsOnOrder=toInteger(r.UnitsOnOrder), p.ReorderLevel=toInteger(r.ReorderLevel),
            p.Discontinued=r.Discontinued
        """, rows=read_csv("Products.csv"))

        print("导入 Customer ...")
        s.run("""
        UNWIND $rows AS r
        MERGE (c:Customer {CustomerID: r.CustomerID})
        SET c.CompanyName=r.CompanyName, c.ContactName=r.ContactName,
            c.ContactTitle=r.ContactTitle, c.City=r.City, c.Country=r.Country,
            c.Phone=r.Phone
        """, rows=read_csv("Customers.csv"))

        print("导入 Employee ...")
        s.run("""
        UNWIND $rows AS r
        MERGE (e:Employee {EmployeeID: r.EmployeeID})
        SET e.FirstName=r.FirstName, e.LastName=r.LastName, e.Title=r.Title,
            e.HireDate=r.HireDate, e.City=r.City, e.Country=r.Country,
            e.ReportsTo=r.ReportsTo
        """, rows=read_csv("Employees.csv"))

        print("导入 Shipper ...")
        s.run("""
        UNWIND $rows AS r
        MERGE (x:Shipper {ShipperID: r.ShipperID})
        SET x.CompanyName=r.CompanyName, x.Phone=r.Phone
        """, rows=read_csv("Shippers.csv"))

        # Order: 主键小写 orderId;CustomerName 从 Customer 反查(预定义 Cypher 用到 o.CustomerName)
        print("导入 Order ...")
        s.run("""
        UNWIND $rows AS r
        MERGE (o:Order {orderId: r.OrderID})
        SET o.CustomerID=r.CustomerID, o.EmployeeID=r.EmployeeID,
            o.OrderDate=r.OrderDate, o.RequiredDate=r.RequiredDate,
            o.ShippedDate=r.ShippedDate, o.ShipVia=r.ShipVia,
            o.Freight=toFloat(r.Freight), o.ShipName=r.ShipName,
            o.ShipCountry=r.ShipCountry
        """, rows=read_csv("Orders.csv"))

        print("导入 Review ...")
        s.run("""
        UNWIND $rows AS r
        MERGE (v:Review {ReviewID: r.ReviewID})
        SET v.ProductID=r.ProductID, v.CustomerID=r.CustomerID,
            v.Rating=toFloat(r.Rating), v.ReviewText=r.ReviewText,
            v.ReviewDate=r.ReviewDate
        """, rows=read_csv("Reviews.csv"))

        # ---------- 关系 ----------
        print("关系 Product-BELONGS_TO->Category ...")
        s.run("""
        MATCH (p:Product), (c:Category) WHERE p.CategoryID = c.CategoryID
        MERGE (p)-[:BELONGS_TO]->(c)
        """)

        print("关系 Product-SUPPLIED_BY->Supplier ...")
        s.run("""
        MATCH (p:Product), (x:Supplier) WHERE p.SupplierID = x.SupplierID
        MERGE (p)-[:SUPPLIED_BY]->(x)
        """)

        print("关系 Customer-PLACED->Order (+ 回填 Order.CustomerName) ...")
        s.run("""
        MATCH (c:Customer), (o:Order) WHERE c.CustomerID = o.CustomerID
        MERGE (c)-[:PLACED]->(o)
        SET o.CustomerName = c.CompanyName
        """)

        print("关系 Employee-PROCESSED->Order ...")
        s.run("""
        MATCH (e:Employee), (o:Order) WHERE e.EmployeeID = o.EmployeeID
        MERGE (e)-[:PROCESSED]->(o)
        """)

        print("关系 Order-SHIPPED_VIA->Shipper ...")
        s.run("""
        MATCH (o:Order), (x:Shipper) WHERE o.ShipVia = x.ShipperID
        MERGE (o)-[:SHIPPED_VIA]->(x)
        """)

        print("关系 Order-CONTAINS->Product ...")
        s.run("""
        UNWIND $rows AS r
        MATCH (o:Order {orderId: r.OrderID}), (p:Product {ProductID: r.ProductID})
        MERGE (o)-[rel:CONTAINS]->(p)
        SET rel.Quantity=toInteger(r.Quantity), rel.UnitPrice=toFloat(r.UnitPrice),
            rel.Discount=toFloat(r.Discount)
        """, rows=read_csv("_Order_Details.csv"))

        print("关系 Employee-REPORTS_TO->Employee ...")
        s.run("""
        MATCH (e:Employee), (m:Employee)
        WHERE e.ReportsTo IS NOT NULL AND e.ReportsTo <> '' AND e.ReportsTo = m.EmployeeID
        MERGE (e)-[:REPORTS_TO]->(m)
        """)

        print("关系 Customer-WROTE->Review ...")
        s.run("""
        MATCH (c:Customer), (v:Review) WHERE c.CustomerID = v.CustomerID
        MERGE (c)-[:WROTE]->(v)
        """)

        print("关系 Review-ABOUT->Product ...")
        s.run("""
        MATCH (v:Review), (p:Product) WHERE v.ProductID = p.ProductID
        MERGE (v)-[:ABOUT]->(p)
        """)

        # ---------- 统计 ----------
        print("\n=== 导入完成,统计 ===")
        for label in ["Product", "Category", "Supplier", "Customer",
                      "Employee", "Shipper", "Order", "Review"]:
            n = s.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
            print(f"  {label:10s}: {n}")
        for rel in ["BELONGS_TO", "SUPPLIED_BY", "PLACED", "PROCESSED",
                    "SHIPPED_VIA", "CONTAINS", "REPORTS_TO", "WROTE", "ABOUT"]:
            n = s.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS c").single()["c"]
            print(f"  {rel:12s}: {n}")

    driver.close()
    print("\nOK")


if __name__ == "__main__":
    main()
