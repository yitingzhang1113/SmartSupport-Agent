"""
Descriptions for predefined Cypher queries.

This module contains detailed descriptions of all predefined Cypher queries
to improve the accuracy of semantic matching. Each description explains the
query's purpose, applicable scenarios, and possible user requests.
"""

# Product query descriptions
PRODUCT_QUERY_DESCRIPTIONS = {
    "product_by_name": "Retrieve information for a specific product, including its price, inventory, and category. Suitable for users requesting details about a particular product.",
    "product_by_category": "Retrieve all products within a specific category. Suitable for users asking which products belong to a given category.",
    "product_by_supplier": "Retrieve all products supplied by a specific supplier. Suitable for users asking which products are provided by a particular supplier.",
    "products_low_stock": "Retrieve products with low inventory (fewer than 10 units in stock). Suitable for users asking which products require restocking or have limited inventory.",
    "products_popular": "Retrieve the most popular products based on the number of reviews. Suitable for users asking which products are the most popular or best-selling.",
}

# Customer query descriptions
CUSTOMER_QUERY_DESCRIPTIONS = {
    "customer_by_name": "Retrieve detailed information for a specific customer. Suitable for users requesting a customer's contact information or address.",
    "customer_orders": "Retrieve all orders placed by a specific customer. Suitable for users requesting a customer's order history.",
    "customer_purchase_history": "Retrieve a customer's purchase history, including purchased products and purchase dates. Suitable for users asking which products a customer has purchased.",
}

# Order query descriptions
ORDER_QUERY_DESCRIPTIONS = {
    "order_by_id": "Retrieve basic information for a specific order by its ID. Suitable for users requesting an order's status, date, or other general information.",
    "order_details": "Retrieve detailed information for a specific order, including products, quantities, and prices. Suitable for users asking which products are included in an order.",
    "recent_orders": "Retrieve the 10 most recent orders. Suitable for users asking about newly placed orders.",
    "delayed_orders": "Retrieve delayed shipment orders. Suitable for users asking which orders have been delayed or were not shipped on time.",
}

# Supplier query descriptions
SUPPLIER_QUERY_DESCRIPTIONS = {
    "supplier_by_country": "Retrieve all suppliers from a specific country. Suitable for users asking which suppliers are located in a given country.",
    "supplier_products": "Retrieve all products supplied by a specific supplier. Suitable for users asking which products are provided by a particular supplier.",
}

# Category query descriptions
CATEGORY_QUERY_DESCRIPTIONS = {
    "all_categories": "Retrieve all product categories and their descriptions. Suitable for users asking which product categories are available.",
    "category_products": "Retrieve all products within a specific category. Suitable for users asking which products belong to a given category.",
    "category_product_count": "Retrieve the number of products in each category. Suitable for users requesting the product distribution across categories.",
}

# Employee query descriptions
EMPLOYEE_QUERY_DESCRIPTIONS = {
    "employee_by_name": "Retrieve basic information for a specific employee. Suitable for users requesting an employee's position, hire date, or other general information.",
    "employee_processed_orders": "Retrieve all orders processed by a specific employee. Suitable for users asking which orders were handled by a particular employee.",
}

# Review query descriptions
REVIEW_QUERY_DESCRIPTIONS = {
    "product_reviews": "Retrieve all reviews for a specific product. Suitable for users requesting customer feedback for a particular product.",
    "top_rated_products": "Retrieve the highest-rated products. Suitable for users asking which products have the highest ratings or the best customer reviews.",
}

# Sales analysis query descriptions
SALES_QUERY_DESCRIPTIONS = {
    "product_sales": "Retrieve the total sales amount for a specific product. Suitable for users requesting sales performance or revenue for a particular product.",
    "category_sales": "Retrieve the total sales amount for each product category. Suitable for users asking which categories generate the highest sales or requesting category sales performance.",
    "monthly_sales": "Retrieve monthly sales statistics. Suitable for users requesting monthly sales trends or revenue changes over time.",
}

# Smart home query descriptions
SMART_HOME_QUERY_DESCRIPTIONS = {
    "smart_home_products": "Retrieve all smart home products. Suitable for users asking which smart home products are available.",
    "smart_speakers": "Retrieve all smart speaker products. Suitable for users asking which smart speakers or voice assistant devices are available.",
    "smart_lighting": "Retrieve all smart lighting products. Suitable for users asking which smart lights or smart lighting devices are available.",
}

# Combine all query descriptions
QUERY_DESCRIPTIONS = {}
QUERY_DESCRIPTIONS.update(PRODUCT_QUERY_DESCRIPTIONS)
QUERY_DESCRIPTIONS.update(CUSTOMER_QUERY_DESCRIPTIONS)
QUERY_DESCRIPTIONS.update(ORDER_QUERY_DESCRIPTIONS)
QUERY_DESCRIPTIONS.update(SUPPLIER_QUERY_DESCRIPTIONS)
QUERY_DESCRIPTIONS.update(CATEGORY_QUERY_DESCRIPTIONS)
QUERY_DESCRIPTIONS.update(EMPLOYEE_QUERY_DESCRIPTIONS)
QUERY_DESCRIPTIONS.update(REVIEW_QUERY_DESCRIPTIONS)
QUERY_DESCRIPTIONS.update(SALES_QUERY_DESCRIPTIONS)
QUERY_DESCRIPTIONS.update(SMART_HOME_QUERY_DESCRIPTIONS)