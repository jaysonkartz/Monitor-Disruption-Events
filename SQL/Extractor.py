import pandas as pd
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
import pyodbc

class SQLExtractor:
    def __init__(self):
        load_dotenv()  # Load environment variables from a .env file
        self.engine = self.create_engine()

    def create_engine(self):
        # Load environment variables
        SQL_SERVER = 'localhost\\SQLEXPRESS'
        SQL_DATABASE = 'DisruptionMonitoring'
        SQL_TRUSTED_CONNECTION = 'yes'
        DRIVER = '{ODBC Driver 17 for SQL Server}'

        # Construct connection string
        connection_string = f"DRIVER={DRIVER};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};Trusted_Connection={SQL_TRUSTED_CONNECTION};"

        connection_url = URL.create(
            "mssql+pyodbc",
            query={"odbc_connect": connection_string}
        )

        try:
            engine = create_engine(connection_url)
            #print("Connected to SQL Server")
            return engine
        except Exception as e:
            print(f"Error connecting to SQL Server: {e}")
            return None

    def load_city_data_from_sql(self):
        if self.engine is None:
            print("No connection to the database.")
            return None

        query = "SELECT TOP 1 * FROM suppliers"
        try:
            with self.engine.connect() as connection:
                city_data = pd.read_sql(query, connection)
            return city_data
        except Exception as e:
            print(f"Error reading data from SQL Server: {e}")
            return None

    def convert_article_data_type(self, article: dict) -> dict:
        """Formats the article data type to match the corresponding data type in the SQL Server database."""
        try:
            article['lat'] = float(article['lat'])
            article['lng'] = float(article['lng'])
            article['Radius'] = float(article['Radius'])
            article['PublishedDate'] = pd.to_datetime(article['PublishedDate'])
            article['created_at'] = pd.to_datetime(article['created_at'])
        except KeyError as e:
            print(f"Key error during data type conversion: {e}")
        except ValueError as e:
            print(f"Value error during data type conversion: {e}")
        return article

    def extract_all_articles(self) -> list[dict]:
        """Extract all articles from the Article table in SQL Server."""
        query = "SELECT * FROM Articles"
        try:
            with self.engine.connect() as connection:
                articles_df = pd.read_sql(query, connection)
            articles = articles_df.to_dict('records')
            articles = [self.convert_article_data_type(article) for article in articles]
            return articles
        except Exception as e:
            print(f"Error reading data from SQL Server: {e}")
            return []

    def extract_all_supplier_info(self) -> list[dict]:
        """Extract all supplier info from the Supplier table in SQL Server."""
        query = "SELECT * FROM suppliers"
        try:
            with self.engine.connect() as connection:
                suppliers_df = pd.read_sql(query, connection)
            suppliers = suppliers_df.to_dict('records')
            return suppliers
        except Exception as e:
            print(f"Error reading data from SQL Server: {e}")
            return []

    def extract_all_unique_disruption_types(self) -> list[str]:
        """Extracts all the unique disruption types from the SQL Server database."""
        query = "SELECT DISTINCT DisruptionType FROM Articles"
        try:
            with self.engine.connect() as connection:
                disruption_types_df = pd.read_sql(query, connection)
            return disruption_types_df['DisruptionType'].tolist()
        except Exception as e:
            print(f"Error reading data from SQL Server: {e}")
            return []

# Example usage:
# if __name__ == "__main__":
#     extractor = SQLExtractor()
    
#     city_data = extractor.load_city_data_from_sql()
#     if city_data is not None:
#         print(city_data)
#     else:
#         print("Failed to load city data.")

#     articles = extractor.extract_all_articles()
#     if articles:
#         for article in articles:
#             print(article)
#     else:
#         print("No articles found or failed to load articles.")

#     suppliers = extractor.extract_all_supplier_info()
#     if suppliers:
#         for supplier in suppliers:
#             print(supplier)
#     else:
#         print("No suppliers found or failed to load suppliers.")

#     disruption_types = extractor.extract_all_unique_disruption_types()
#     if disruption_types:
#         print("Unique Disruption Types:")
#         for disruption_type in disruption_types:
#             print(disruption_type)
#     else:
#         print("No disruption types found or failed to load disruption types.")
