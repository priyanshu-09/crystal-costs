
import os
import snowflake.connector as snow
import json

class Snowflake:
    def __init__(self):
        self.account = os.environ.get("SNOWFLAKE_ACCOUNT", "")
        self.user = os.environ.get("SNOWFLAKE_USER", "")
        self.password = os.environ.get("SNOWFLAKE_PASSWORD", "")
        self.warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE", "")
        self.database = 'SNOWFLAKE'
        self.schema = 'ACCOUNT_USAGE'
        self.role = os.environ.get("SNOWFLAKE_ROLE", "")
        
        self.playground_database = "PREDICTION_ARCTIC_DB"
        self.playground_schema = "WAREHOUSE_METERING_PREDICTIONS"

    def get_snowflake_connection_url(self):
        return f"snowflake://{self.user}:{self.password}@{self.account}/{self.database}/{self.schema}?warehouse={self.warehouse}&role={self.role}"
    
    def get_snowflake_connection(self, playground=False):
        return snow.connect(
            user=self.user,
            password=self.password,
            account=self.account,
            warehouse=self.warehouse,
            database=self.playground_database if playground else self.database,
            schema=self.playground_schema if playground else self.schema
        )
    
    def sf_forecast_call(self, timestamp_column, value_column, days):
        try:
            conn = self.get_snowflake_connection(playground=True)
            model_name = self.__get_model_name()
            with conn.cursor() as cur: 
                create_model_query = f"""
                    CREATE OR REPLACE SNOWFLAKE.ML.FORECAST {model_name}(
                        INPUT_DATA => SYSTEM$REFERENCE('VIEW', 'credit_usage_view'),
                        TIMESTAMP_COLNAME => '{timestamp_column}',
                        TARGET_COLNAME => '{value_column}'
                    )
                """
                inference_query = f"CALL {model_name}!FORECAST(FORECASTING_PERIODS => {days});"
                drop_model = f"DROP SNOWFLAKE.ML.FORECAST {model_name}"

                _ = cur.execute(create_model_query)
                data = cur.execute(inference_query).fetchall()
                _ = cur.execute(drop_model)
                return data
        except Exception as e:
            print("Issue with quering data", e)
        finally:
            conn.close()

    def __get_model_name(self) -> str:
        return "credit_usage_model"
    
    def call_arctic_complete(self, messages):
        conn = self.get_snowflake_connection()
        with conn.cursor() as cur:
            sql = "SELECT snowflake.cortex.complete('snowflake-arctic', " + str(messages) +", {}) AS llm_response"
          
            cur.execute(sql)
            data = json.loads(cur.fetchall()[0][0])
        conn.close()

        return data.get("choices", [{}])[0].get("messages", "")