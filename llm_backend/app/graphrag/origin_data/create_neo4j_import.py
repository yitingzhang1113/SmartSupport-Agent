#GRAPH Data PREPARATION
import pandas as pd
import os
import re
from datetime import datetime
from pathlib import Path, PureWindowsPath

NODE_FILES = {
    "Product": "product_nodes.csv",
    "Category": "category_nodes.csv",
    "Supplier": "supplier_nodes.csv",
    "Customer": "customer_nodes.csv",
    "Employee": "employee_nodes.csv",
    "Shipper": "shipper_nodes.csv",
    "Order": "order_nodes.csv",
    "Review": "review_nodes.csv",
}


RELATIONSHIP_FILES = {
    "BELONGS_TO": "product_category_edges.csv",
    "SUPPLIED_BY": "product_supplier_edges.csv",
    "PLACED": "customer_order_edges.csv",
    "PROCESSED": "employee_order_edges.csv",
    "SHIPPED_VIA": "order_shipper_edges.csv",
    "CONTAINS": "order_product_edges.csv",
    "REPORTS_TO": "employee_reports_to_edges.csv",
    "WROTE": "customer_review_edges.csv",
    "ABOUT": "review_product_edges.csv",
}

def prepare_neo4j_admin_import(data_dir="exported_data",output_dir="output_data/data/neo4j_admin",windows_import_dir=r"D:\smart_support_neo4j_import",windows_neo4j_home=r"D:\downloads\neo4j-community-2026.05.0",):
    """
    Prepare Neo4j Admin import files with the required header columns.

    Parameters
    ----------
    data_dir : str
        Directory containing the source CSV files.
    output_dir : str
        Directory used to store the generated Neo4j Admin import files.
    """

    print("Starting to prepare Neo4j Admin import files...")

    # Ensure that the output directory exists.
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Prepare node files.
    prepare_product_nodes(data_dir, output_dir)
    prepare_category_nodes(data_dir, output_dir)
    prepare_supplier_nodes(data_dir, output_dir)
    prepare_customer_nodes(data_dir, output_dir)
    prepare_employee_nodes(data_dir, output_dir)
    prepare_shipper_nodes(data_dir, output_dir)
    prepare_order_nodes(data_dir, output_dir)
    prepare_review_nodes(data_dir, output_dir)

    # Prepare relationship files.
    prepare_product_category_edges(data_dir, output_dir)
    prepare_product_supplier_edges(data_dir, output_dir)
    prepare_customer_order_edges(data_dir, output_dir)
    prepare_employee_order_edges(data_dir, output_dir)
    prepare_order_shipper_edges(data_dir, output_dir)
    prepare_order_product_edges(data_dir, output_dir)
    prepare_employee_reports_to_edges(data_dir, output_dir)
    prepare_review_edges(data_dir, output_dir)

    print("Neo4j Admin import files have been prepared successfully. "f"Files are stored in: {output_dir}")

    # Generate the Neo4j Admin import command.
    # generate_import_command(output_dir)
    generate_windows_import_command(command_output_dir=output_dir,windows_import_dir=windows_import_dir,windows_neo4j_home=windows_neo4j_home)

    generate_linux_import_command(output_dir=output_dir)


def prepare_product_nodes(data_dir, output_dir):
    """Prepare the Product node import file."""

    file_path = os.path.join(data_dir, "products.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Product data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        # Rename the ID column using the Neo4j Admin import format.
        df = df.rename(columns={"ProductID": "productId:ID(Product)"})

        # Add the node label column.
        df["labels:LABEL"] = "Product"

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"product_nodes.csv")

        df.to_csv(output_file,index=False)

        print(f"Product node file saved: {output_file}")

    except Exception as e:
        print(f"An error occurred while preparing Product nodes: {e}")


def prepare_category_nodes(data_dir, output_dir):
    """Prepare the Category node import file."""

    file_path = os.path.join(data_dir,"categories.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Category data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        # Rename the ID column using the Neo4j Admin import format.
        df = df.rename(columns={"CategoryID": "categoryId:ID(Category)"})

        # Add the node label column.
        df["labels:LABEL"] = "Category"

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"category_nodes.csv")

        df.to_csv(output_file,index=False)

        print(f"Category node file saved: {output_file}")

    except Exception as e:
        print(f"An error occurred while preparing Category nodes: {e}")


def prepare_supplier_nodes(data_dir, output_dir):
    """Prepare the Supplier node import file."""

    file_path = os.path.join(data_dir,"suppliers.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Supplier data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        # Rename the ID column using the Neo4j Admin import format.
        df = df.rename(columns={"SupplierID": "supplierId:ID(Supplier)"})

        # Add the node label column.
        df["labels:LABEL"] = "Supplier"

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"supplier_nodes.csv")

        df.to_csv(output_file,index=False)

        print(f"Supplier node file saved: {output_file}")

    except Exception as e:
        print(f"An error occurred while preparing Supplier nodes: {e}")


def prepare_customer_nodes(data_dir, output_dir):
    """Prepare the Customer node import file."""

    file_path = os.path.join(data_dir,"customers.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Customer data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        # Rename the ID column using the Neo4j Admin import format.
        df = df.rename(columns={"CustomerID": "customerId:ID(Customer)"})

        # Add the node label column.
        df["labels:LABEL"] = "Customer"

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"customer_nodes.csv")

        df.to_csv(output_file,index=False)

        print(f"Customer node file saved: {output_file}")

    except Exception as e:
        print(f"An error occurred while preparing Customer nodes: {e}")


def prepare_employee_nodes(data_dir, output_dir):
    """Prepare the Employee node import file."""

    file_path = os.path.join(data_dir,"employees.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Employee data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        # Rename the ID column using the Neo4j Admin import format.
        df = df.rename(columns={"EmployeeID": "employeeId:ID(Employee)"})

        # Add the node label column.
        df["labels:LABEL"] = "Employee"

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"employee_nodes.csv")

        df.to_csv(output_file,index=False)

        print(f"Employee node file saved: {output_file}")

    except Exception as e:
        print(f"An error occurred while preparing Employee nodes: {e}")


def prepare_shipper_nodes(data_dir, output_dir):
    """Prepare the Shipper node import file."""

    file_path = os.path.join(data_dir,"shippers.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Shipper data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        # Rename the ID column using the Neo4j Admin import format.
        df = df.rename(columns={"ShipperID": "shipperId:ID(Shipper)"})

        # Add the node label column.
        df["labels:LABEL"] = "Shipper"

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"shipper_nodes.csv")

        df.to_csv(output_file,index=False)

        print(f"Shipper node file saved: {output_file}")

    except Exception as e:
        print(f"An error occurred while preparing Shipper nodes: {e}")


def prepare_order_nodes(data_dir, output_dir):
    """Prepare the Order node import file."""

    file_path = os.path.join(data_dir,"orders.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Order data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        # Rename the ID column using the Neo4j Admin import format.
        df = df.rename(columns={"OrderID": "orderId:ID(Order)"})

        # Add the node label column.
        df["labels:LABEL"] = "Order"

        # Remove foreign-key columns because they will be used
        # to create relationship files.
        if "CustomerID" in df.columns:
            df = df.drop(columns=["CustomerID"])

        if "EmployeeID" in df.columns:
            df = df.drop(columns=["EmployeeID"])

        if "ShipVia" in df.columns:
            df = df.drop(columns=["ShipVia"])

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"order_nodes.csv")

        df.to_csv(output_file,index=False)

        print(f"Order node file saved: {output_file}")

    except Exception as e:
        print(f"An error occurred while preparing Order nodes: {e}")


def prepare_review_nodes(data_dir, output_dir):
    """Prepare the Review node import file."""

    file_path = os.path.join(data_dir,"reviews.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Review data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        # Rename the ID column using the Neo4j Admin import format.
        df = df.rename(columns={"ReviewID": "reviewId:ID(Review)"
            })

        # Add the node label column.
        df["labels:LABEL"] = "Review"

        # Remove foreign-key columns because they will be used
        # to create relationship files.
        if "ProductID" in df.columns:
            df = df.drop(columns=["ProductID"])

        if "CustomerID" in df.columns:
            df = df.drop(columns=["CustomerID"])

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"review_nodes.csv")

        df.to_csv(output_file,index=False)

        print(f"Review node file saved: {output_file}")

    except Exception as e:
        print(f"An error occurred while preparing Review nodes: {e}")


def prepare_product_category_edges(data_dir,output_dir):
    """Prepare the Product-to-Category relationship file."""

    file_path = os.path.join(data_dir,"products.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Product data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        if ("ProductID" not in df.columns
            or "CategoryID" not in df.columns):
            print(    "Warning: Product data is missing "
                "the ProductID or CategoryID column."
            )
            return

        # Create the relationship DataFrame.  (:Product)-[BELONGS_TO]->(：Category)
        edges_df = pd.DataFrame({
            ":START_ID(Product)": df["ProductID"],
            ":END_ID(Category)": df["CategoryID"],
            ":TYPE": "BELONGS_TO",
            })

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"product_category_edges.csv")

        edges_df.to_csv(output_file,index=False)

        print("Product-to-Category relationship file saved: "f"{output_file}")

    except Exception as e:
        print("An error occurred while preparing "f"Product-to-Category relationships: {e}")


def prepare_product_supplier_edges(data_dir,output_dir):
    """Prepare the Product-to-Supplier relationship file."""

    file_path = os.path.join(data_dir,"products.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Product data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        if ("ProductID" not in df.columns
            or "SupplierID" not in df.columns):
            print(    "Warning: Product data is missing "
                "the ProductID or SupplierID column."
            )
            return

        # Create the relationship DataFrame.(:Product)-[SUPPLIED_BY]->(：Supplier)
        edges_df = pd.DataFrame({
                ":START_ID(Product)": df["ProductID"],
                ":END_ID(Supplier)": df["SupplierID"],
                ":TYPE": "SUPPLIED_BY",
            })

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"product_supplier_edges.csv")

        edges_df.to_csv(output_file,index=False)

        print("Product-to-Supplier relationship file saved: "f"{output_file}")

    except Exception as e:
        print("An error occurred while preparing "f"Product-to-Supplier relationships: {e}")


def prepare_customer_order_edges(data_dir,output_dir):
    """Prepare the Customer-to-Order relationship file."""

    file_path = os.path.join(data_dir,"orders.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Order data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        if ("CustomerID" not in df.columns or "OrderID" not in df.columns):
            print("Warning: Order data is missing ""the CustomerID or OrderID column.")
            return

        # Create the relationship DataFrame.
        edges_df = pd.DataFrame({
                ":START_ID(Customer)": df["CustomerID"],
                ":END_ID(Order)": df["OrderID"],
                ":TYPE": "PLACED",
            })

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"customer_order_edges.csv")

        edges_df.to_csv(output_file,index=False)

        print("Customer-to-Order relationship file saved: "f"{output_file}")

    except Exception as e:
        print("An error occurred while preparing "f"Customer-to-Order relationships: {e}")


def prepare_employee_order_edges(data_dir,output_dir):
    """Prepare the Employee-to-Order relationship file."""

    file_path = os.path.join(data_dir,"orders.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Order data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        if ("EmployeeID" not in df.columns or "OrderID" not in df.columns):
            print("Warning: Order data is missing ""the EmployeeID or OrderID column.")
            return

        # Create the relationship DataFrame.
        edges_df = pd.DataFrame({
                ":START_ID(Employee)": df["EmployeeID"],
                ":END_ID(Order)": df["OrderID"],
                ":TYPE": "PROCESSED",
            })

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"employee_order_edges.csv")

        edges_df.to_csv(output_file,index=False)

        print("Employee-to-Order relationship file saved: "f"{output_file}")

    except Exception as e:
        print("An error occurred while preparing "f"Employee-to-Order relationships: {e}")


def prepare_order_shipper_edges(data_dir,output_dir):
    """Prepare the Order-to-Shipper relationship file."""

    file_path = os.path.join(data_dir,"orders.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Order data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        if ("OrderID" not in df.columns or "ShipVia" not in df.columns):
            print("Warning: Order data is missing "
                "the OrderID or ShipVia column.")
            return

        # Create the relationship DataFrame.
        edges_df = pd.DataFrame({
                ":START_ID(Order)": df["OrderID"],
                ":END_ID(Shipper)": df["ShipVia"],
                ":TYPE": "SHIPPED_VIA",
            })

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"order_shipper_edges.csv")

        edges_df.to_csv(output_file,index=False)

        print("Order-to-Shipper relationship file saved: "f"{output_file}")

    except Exception as e:
        print("An error occurred while preparing "f"Order-to-Shipper relationships: {e}")


def prepare_order_product_edges(data_dir,output_dir):
    """Prepare the Order-to-Product relationship file."""

    file_path = os.path.join(data_dir,"order_details.csv")

    if not os.path.exists(file_path):
        print("Warning: Order detail data file not found: "f"{file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        if ("OrderID" not in df.columns
            or "ProductID" not in df.columns):
            print(    "Warning: Order detail data is missing "
                "the OrderID or ProductID column."
            )
            return

        # Create the relationship DataFrame.
        edges_df = pd.DataFrame({
                ":START_ID(Order)": df["OrderID"],
                ":END_ID(Product)": df["ProductID"],
                ":TYPE": "CONTAINS",
                "UnitPrice": df["UnitPrice"],
                "Quantity": df["Quantity"],
                "Discount": df["Discount"],
            })

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"order_product_edges.csv")

        edges_df.to_csv(output_file,index=False)

        print("Order-to-Product relationship file saved: "f"{output_file}")

    except Exception as e:
        print("An error occurred while preparing "f"Order-to-Product relationships: {e}")


def prepare_employee_reports_to_edges(data_dir,output_dir):
    """Prepare the Employee reporting relationship file."""

    file_path = os.path.join(data_dir,"employees.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Employee data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        if ("EmployeeID" not in df.columns
            or "ReportsTo" not in df.columns):
            print("Warning: Employee data is missing "
            "the EmployeeID or ReportsTo column.")
            return

        # Remove rows where ReportsTo is empty.
        df = df.dropna(subset=["ReportsTo"])

        # Create the relationship DataFrame.
        edges_df = pd.DataFrame({
                ":START_ID(Employee)": df["EmployeeID"],
                ":END_ID(Employee)": df["ReportsTo"],
                ":TYPE": "REPORTS_TO",
            })

        # Save the file in Neo4j Admin import format.
        output_file = os.path.join(output_dir,"employee_reports_to_edges.csv")

        edges_df.to_csv(output_file,index=False)

        print("Employee reporting relationship file saved: "f"{output_file}")

    except Exception as e:
        print("An error occurred while preparing "f"Employee reporting relationships: {e}")


def prepare_review_edges(data_dir,output_dir):
    """Prepare Review relationship files."""

    file_path = os.path.join(data_dir,"reviews.csv")

    if not os.path.exists(file_path):
        print(f"Warning: Review data file not found: {file_path}")
        return

    try:
        df = pd.read_csv(file_path)

        # 1. Customer-to-Review relationship.
        if ("CustomerID" in df.columns and "ReviewID" in df.columns):
            customer_review_edges = pd.DataFrame(    {
                    ":START_ID(Customer)": df["CustomerID"],
                    ":END_ID(Review)": df["ReviewID"],
                    ":TYPE": "WROTE",
                }
            )

            output_file = os.path.join(output_dir, 'customer_review_edges.csv')
            customer_review_edges.to_csv(output_file, index=False)

            print("Customer-to-Review relationship file saved: "f"{output_file}")

        # 2. Review-to-Product relationship.
        if ("ReviewID" in df.columns and "ProductID" in df.columns):
            review_product_edges = pd.DataFrame(    
                {
                    ":START_ID(Review)": df["ReviewID"],
                    ":END_ID(Product)": df["ProductID"],
                    ":TYPE": "ABOUT",
                }
            )

            output_file = os.path.join(output_dir, 'review_product_edges.csv')
            review_product_edges.to_csv(output_file, index=False)

            print("Review-to-Product relationship file saved: "f"{output_file}")

    except Exception as e:
        print("An error occurred while preparing "f"Review relationships: {e}")


def generate_import_command(output_dir):
    """
    Generate a Neo4j Admin import command for Neo4j 2025.02.0
    and later versions.
    """

    command_path = os.path.join(output_dir, 'import_command.bat')

    with open(command_path, 'w') as f:
        f.write("@echo off\n\n")
        f.write("REM Neo4j Admin import command\n")
        f.write("REM Compatible with Neo4j 2025.02.0 ""and later versions\n")
        f.write("REM Generated at: "+ datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")

        f.write("neo4j-admin database import full neo4j --overwrite-destination ^\n")
        f.write(f"  --nodes=Product=\"{os.path.abspath(os.path.join(output_dir, 'product_nodes.csv'))}\" ^\n")
        f.write(f"  --nodes=Category=\"{os.path.abspath(os.path.join(output_dir, 'category_nodes.csv'))}\" ^\n")
        f.write(f"  --nodes=Supplier=\"{os.path.abspath(os.path.join(output_dir, 'supplier_nodes.csv'))}\" ^\n")
        f.write(f"  --nodes=Customer=\"{os.path.abspath(os.path.join(output_dir, 'customer_nodes.csv'))}\" ^\n")
        f.write(f"  --nodes=Employee=\"{os.path.abspath(os.path.join(output_dir, 'employee_nodes.csv'))}\" ^\n")
        f.write(f"  --nodes=Shipper=\"{os.path.abspath(os.path.join(output_dir, 'shipper_nodes.csv'))}\" ^\n")
        f.write(f"  --nodes=Order=\"{os.path.abspath(os.path.join(output_dir, 'order_nodes.csv'))}\" ^\n")
        f.write(f"  --nodes=Review=\"{os.path.abspath(os.path.join(output_dir, 'review_nodes.csv'))}\" ^\n")
        f.write(f"  --relationships=BELONGS_TO=\"{os.path.abspath(os.path.join(output_dir, 'product_category_edges.csv'))}\" ^\n")
        f.write(f"  --relationships=SUPPLIED_BY=\"{os.path.abspath(os.path.join(output_dir, 'product_supplier_edges.csv'))}\" ^\n")
        f.write(f"  --relationships=PLACED=\"{os.path.abspath(os.path.join(output_dir, 'customer_order_edges.csv'))}\" ^\n")
        f.write(f"  --relationships=PROCESSED=\"{os.path.abspath(os.path.join(output_dir, 'employee_order_edges.csv'))}\" ^\n")
        f.write(f"  --relationships=SHIPPED_VIA=\"{os.path.abspath(os.path.join(output_dir, 'order_shipper_edges.csv'))}\" ^\n")
        f.write(f"  --relationships=CONTAINS=\"{os.path.abspath(os.path.join(output_dir, 'order_product_edges.csv'))}\" ^\n")
        f.write(f"  --relationships=REPORTS_TO=\"{os.path.abspath(os.path.join(output_dir, 'employee_reports_to_edges.csv'))}\" ^\n")
        f.write(f"  --relationships=WROTE=\"{os.path.abspath(os.path.join(output_dir, 'customer_review_edges.csv'))}\" ^\n")
        f.write(f"  --relationships=ABOUT=\"{os.path.abspath(os.path.join(output_dir, 'review_product_edges.csv'))}\" ^\n")
        f.write("  --delimiter=\",\" ^\n")
        f.write("  --array-delimiter=\";\" ^\n")
        f.write("  --skip-bad-relationships=true ^\n")
        f.write("  --skip-duplicate-nodes=true\n")
    print("Neo4j Admin import command for Neo4j "f"and later versions saved: {command_path}")


def generate_linux_import_command(
    output_dir: str,
    neo4j_home: str = "/opt/neo4j",
) -> None:
    output_path = Path(output_dir).resolve()

    command_path = (output_path
        / "import_command_linux.sh"
    )

    neo4j_admin = (Path(neo4j_home)
        / "bin"
        / "neo4j-admin"
    )

    arguments: list[str] = []

    for label, filename in NODE_FILES.items():
        file_path = output_path / filename
        arguments.append(f'  --nodes={label}="{file_path}"')

    for rel_type, filename in (RELATIONSHIP_FILES.items()
    ):
        file_path = output_path / filename
        arguments.append((    f'  --relationships={rel_type}='
                f'"{file_path}"'
            ))

    arguments.extend([
            '  --delimiter=","',
            '  --array-delimiter=";"',
            "--multiline-fields=true",
            "--skip-bad-relationships=true",
            "--skip-duplicate-nodes=true",])

    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        (f'"{neo4j_admin}" '
            "database import full neo4j "
            "--overwrite-destination=true \\"),
    ]

    for index, argument in enumerate(arguments):
        is_last = index == len(arguments) - 1

        if is_last:
            lines.append(argument)
        else:
            lines.append(f"{argument} \\")

    command_path.write_text("\n".join(lines) + "\n",
        encoding="utf-8",
    )

    command_path.chmod(0o755)

    print(f"Linux import command saved: {command_path}")

def generate_windows_import_command(
    command_output_dir: str,
    windows_import_dir: str,
    windows_neo4j_home: str,
) -> None:
    command_path = Path(command_output_dir,"import_command_windows.bat")

    import_dir = PureWindowsPath(windows_import_dir)

    neo4j_admin = PureWindowsPath(windows_neo4j_home,"bin","neo4j-admin.bat")

    node_files = {
        "Product": "product_nodes.csv",
        "Category": "category_nodes.csv",
        "Supplier": "supplier_nodes.csv",
        "Customer": "customer_nodes.csv",
        "Employee": "employee_nodes.csv",
        "Shipper": "shipper_nodes.csv",
        "Order": "order_nodes.csv",
        "Review": "review_nodes.csv",
    }

    relationship_files = {
        "BELONGS_TO": "product_category_edges.csv",
        "SUPPLIED_BY": "product_supplier_edges.csv",
        "PLACED": "customer_order_edges.csv",
        "PROCESSED": "employee_order_edges.csv",
        "SHIPPED_VIA": "order_shipper_edges.csv",
        "CONTAINS": "order_product_edges.csv",
        "REPORTS_TO": "employee_reports_to_edges.csv",
        "WROTE": "customer_review_edges.csv",
        "ABOUT": "review_product_edges.csv",
    }

    lines = [
        "@echo off",
        "setlocal",
        "",
        (f'"{neo4j_admin}" '
            "database import full neo4j "
            "--overwrite-destination=true ^"),
    ]

    arguments: list[str] = []

    for label, filename in node_files.items():
        file_path = import_dir / filename
        arguments.append(f'  --nodes={label}="{file_path}"')

    for rel_type, filename in relationship_files.items():
        file_path = import_dir / filename
        arguments.append(f'  --relationships={rel_type}="{file_path}"')

    arguments.extend([
            '  --delimiter=","',
            '  --array-delimiter=";"',
            "--multiline-fields=true",
            "--skip-bad-relationships=true",
            "--skip-duplicate-nodes=true",])

    for index, argument in enumerate(arguments):
        is_last = index == len(arguments) - 1
        lines.append(argument if is_last else f"{argument} ^")

    lines.extend([
            "",
            "if errorlevel 1 (",
            "  echo Neo4j import failed.",
            "  pause",
            "  exit /b 1",
            ")",
            "",
            "echo Neo4j import completed successfully.",
            "pause",
            "endlocal",])

    command_path.write_text("\n".join(lines) + "\n",encoding="utf-8")

    print(f"Windows import command saved: {command_path}")

if __name__ == "__main__":
    # When this script is executed directly, process the files
    # from the default input directory.
    prepare_neo4j_admin_import()

