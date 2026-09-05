from typing import Any
import re
from app.lg_agent.kg_sub_graph.agentic_rag_agents.retrievers.cypher_examples.base import BaseCypherExampleRetriever

class NorthwindCypherRetriever(BaseCypherExampleRetriever):
    """
    Cypher example retriever generated from real data.
    """
    
    def get_examples(self, query: str, k: int = 5) -> str:
        """
        Return relevant Cypher query examples based on the user query.
        
        Parameters
        ----------
        query : str
            The user's natural language query.
        k : int, optional
            Number of examples to return, by default 5.
            
        Returns
        -------
        str
            Formatted example string; each example contains a question and its corresponding Cypher query.
        """
        # TODO: Retrieve examples from persistent storage in MySQL, Redis
        # Organize examples by category
        all_examples = {
            "Product Queries": [
                {
                    "question": "Find all smart speaker products",
                    "cypher": """MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
                    WHERE c.CategoryName = 'Smart Speaker'
                    RETURN p.ProductName, p.UnitPrice, p.UnitsInStock"""
                },
                {
                    "question": "Find products with stock lower than 20",
                    "cypher": """MATCH (p:Product)
                    WHERE p.UnitsInStock < 20
                    RETURN p.ProductName, p.UnitsInStock
                    ORDER BY p.UnitsInStock"""
                },
                {
                    "question": "Which products are priced above 500 dollars?",
                    "cypher": """MATCH (p:Product)
                    WHERE p.UnitPrice > 500
                    RETURN p.ProductName, p.UnitPrice
                    ORDER BY p.UnitPrice DESC"""
                }
            ],

            "Product Categories": [
                {
                    "question": "What smart home product categories are available?",
                    "cypher": """MATCH (c:Category)
                    RETURN c.CategoryName, c.Description"""
                },
                {
                    "question": "What products are in the smart lighting category?",
                    "cypher": """MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
                    WHERE c.CategoryName = 'Smart Lighting'
                    RETURN p.ProductName, p.UnitPrice"""
                }
            ],

            "Supplier Queries": [
                {
                    "question": "What products are supplied by Google Nest?",
                    "cypher": """MATCH (p:Product)-[:SUPPLIED_BY]->(s:Supplier)
                    WHERE s.CompanyName = 'Google Nest'
                    RETURN p.ProductName, p.QuantityPerUnit, p.UnitPrice"""
                },
                {
                    "question": "What products are supplied by US suppliers?",
                    "cypher": """MATCH (p:Product)-[:SUPPLIED_BY]->(s:Supplier)
                    WHERE s.Country = 'USA'
                    RETURN s.CompanyName, p.ProductName, p.UnitPrice"""
                }
            ],

            "Order Queries": [
                {
                    "question": "What products are included in order 1?",
                    "cypher": """MATCH (o:Order)-[:CONTAINS]->(p:Product)
                    WHERE o.OrderID = 1
                    RETURN p.ProductName, p.UnitPrice, o.OrderDate"""
                },
                {
                    "question": "Who processed order 1?",
                    "cypher": """MATCH (o:Order)<-[:PROCESSED]-(e:Employee)
                    WHERE o.OrderID = 1
                    RETURN e.FirstName, e.LastName, e.Title"""
                },
                {
                    "question": "What orders were placed by customer AB123?",
                    "cypher": """MATCH (o:Order)<-[:PLACED]-(c:Customer)
                    WHERE c.CustomerID = 'AB123'
                    RETURN o.OrderID, o.OrderDate, o.ShippedDate
                    ORDER BY o.OrderDate DESC"""
                }
            ],

            "Employee Queries": [
                {
                    "question": "What orders were processed by John Smith?",
                    "cypher": """MATCH (o:Order)<-[:PROCESSED]-(e:Employee)
                    WHERE e.FirstName = 'John' AND e.LastName = 'Smith'
                    RETURN o.OrderID, o.OrderDate, o.ShippedDate
                    ORDER BY o.OrderDate DESC"""
                },
                {
                    "question": "Who reports to Michael Johnson?",
                    "cypher": """MATCH (e1:Employee)-[:REPORTS_TO]->(e2:Employee)
                    WHERE e2.FirstName = 'Michael' AND e2.LastName = 'Johnson'
                    RETURN e1.FirstName, e1.LastName, e1.Title"""
                }
            ],

            "Shipping Queries": [
                {
                    "question": "Which shipping company delivered order 1?",
                    "cypher": """MATCH (o:Order)-[:SHIPPED_VIA]->(s:Shipper)
                    WHERE o.OrderID = 1
                    RETURN s.CompanyName, s.Phone, o.ShippedDate"""
                },
                {
                    "question": "Which orders were shipped by FedEx?",
                    "cypher": """MATCH (o:Order)-[:SHIPPED_VIA]->(s:Shipper)
                    WHERE s.CompanyName = 'FedEx'
                    RETURN o.OrderID, o.ShipName, o.ShipAddress, o.ShipCity, o.ShippedDate
                    LIMIT 10"""
                }
            ],

            "Customer Queries": [
                {
                    "question": "Which customers are from Seattle?",
                    "cypher": """MATCH (c:Customer)
                    WHERE c.City = 'Seattle'
                    RETURN c.CompanyName, c.ContactName, c.Phone"""
                },
                {
                    "question": "Where were orders from TechHome Solutions shipped?",
                    "cypher": """MATCH (o:Order)<-[:PLACED]-(c:Customer)
                    WHERE c.CompanyName = 'TechHome Solutions'
                    RETURN o.OrderID, o.ShipAddress, o.ShipCity, o.ShipCountry"""
                }
            ],

            "Complex Queries": [
                {
                    "question": "What are the best-selling smart home products?",
                    "cypher": """MATCH (o:Order)-[rel:CONTAINS]->(p:Product)
                    WITH p.ProductName AS product, SUM(rel.Quantity) AS total_quantity
                    RETURN product, total_quantity
                    ORDER BY total_quantity DESC
                    LIMIT 5"""
                },
                {
                    "question": "Which suppliers provide the products in order 1?",
                    "cypher": """MATCH (o:Order)-[:CONTAINS]->(p:Product)-[:SUPPLIED_BY]->(s:Supplier)
                    WHERE o.OrderID = 1
                    RETURN p.ProductName, s.CompanyName, s.ContactName, s.Phone"""
                },
                {
                    "question": "Which smart speaker products were included in orders processed by John Smith?",
                    "cypher": """MATCH (e:Employee)<-[:PROCESSED]-(o:Order)-[:CONTAINS]->(p:Product)-[:BELONGS_TO]->(c:Category)
                    WHERE e.FirstName = 'John' AND e.LastName = 'Smith' AND c.CategoryName = 'Smart Speaker'
                    RETURN DISTINCT p.ProductName, p.UnitPrice, o.OrderID
                    ORDER BY p.ProductName"""
                }
            ],

            "Product Reviews and Manuals": [
                {
                    "question": "Show reviews for Amazon Echo Smart Speaker Pro",
                    "cypher": """MATCH (p:Product)<-[:ABOUT]-(r:Review)
                    WHERE p.ProductName = 'Amazon Echo Smart Speaker Pro'
                    RETURN r.ReviewText, r.Rating, r.ReviewDate
                    ORDER BY r.ReviewDate DESC"""
                },
                {
                    "question": "Which smart lock products have ratings above 4.5?",
                    "cypher": """MATCH (p:Product)-[:BELONGS_TO]->(c:Category), (p)<-[:ABOUT]-(r:Review)
                    WHERE c.CategoryName = 'Smart Lock' AND r.Rating > 4.5
                    RETURN p.ProductName, AVG(r.Rating) AS average_rating, COUNT(r) AS review_count
                    ORDER BY average_rating DESC"""
                }
            ],

            "Order Statistics": [
                {
                    "question": "Show monthly order counts",
                    "cypher": """MATCH (o:Order)
                    WITH SUBSTRING(o.OrderDate, 0, 7) AS month, COUNT(o) AS order_count
                    RETURN month, order_count
                    ORDER BY month"""
                },
                {
                    "question": "Show sales amount by product category",
                    "cypher": """MATCH (o:Order)-[rel:CONTAINS]->(p:Product)-[:BELONGS_TO]->(c:Category)
                    WITH c.CategoryName AS category, SUM(rel.UnitPrice * rel.Quantity * (1-rel.Discount)) AS total_sales
                    RETURN category, total_sales
                    ORDER BY total_sales DESC"""
                }
            ],

            "Geographic Analysis": [
                {
                    "question": "Show customer counts by city",
                    "cypher": """MATCH (c:Customer)
                    WITH c.City AS city, COUNT(c) AS customer_count
                    RETURN city, customer_count
                    ORDER BY customer_count DESC
                    LIMIT 10"""
                },
                {
                    "question": "Show order count and sales amount by state",
                    "cypher": """MATCH (c:Customer)-[:PLACED]->(o:Order)-[rel:CONTAINS]->(p:Product)
                    WITH c.Region AS state, COUNT(DISTINCT o) AS order_count,
                        SUM(rel.UnitPrice * rel.Quantity * (1-rel.Discount)) AS sales
                    RETURN state, order_count, sales
                    ORDER BY sales DESC"""
                }
            ]
        }
        
         # Flatten all examples
        examples = []
        for category_examples in all_examples.values():
            examples.extend(category_examples)
        
        # Basic relevance matching
        def compute_relevance(example, query):
            # Match by keywords
            score = 0
            query_words = set(re.findall(r'\w+', query.lower()))
            example_words = set(re.findall(r'\w+', example["question"].lower()))
            

            # TODO: Compute relevance using embeddings. Implementation approach:
            # 1. Convert the user question and example questions to embedding vectors
            # 2. Compute cosine similarity between the two vectors
            # 3. Return relevance score based on cosine similarity

            # Count word overlap
            overlap = len(query_words.intersection(example_words))
            if overlap > 0:
                score += overlap * 2
            
            # Check whether specific keywords are present
            important_patterns = [
                (r'product|item|goods', 'Product'),
                (r'category|type|classification', 'Category'),
                (r'supplier|vendor|provider', 'Supplier'),
                (r'order|purchase', 'Order'),
                (r'customer|client', 'Customer'),
                (r'employee|staff|manager', 'Employee'),
                (r'shipping|delivery|shipper|carrier', 'Shipping'),
                (r'review|rating|comment|feedback', 'Review'),
                (r'manual|guide|instruction', 'Manual')
            ]
            
            for pattern, category in important_patterns:
                if re.search(pattern, query):
                    # Increase score if the example question also contains the related pattern
                    if re.search(pattern, example["question"]):
                        score += 3
                    
                    # Check whether it belongs to a related category
                    for cat, cat_examples in all_examples.items():
                        if category in cat and example in cat_examples:
                            score += 2
            
            return score
        
        # Compute relevance score for each example against the query
        scored_examples = [(example, compute_relevance(example, query)) for example in examples]
        
        # Sort by relevance and select top k
        scored_examples.sort(key=lambda x: x[1], reverse=True)
        selected_examples = [example for example, _ in scored_examples[:k]]
        

        # Format for text2cypher expected format
        formatted_examples = "\n\n".join([
            f"Question: {example['question']}\nCypher: {example['cypher']}"
            for example in selected_examples
        ])
        
        return formatted_examples
