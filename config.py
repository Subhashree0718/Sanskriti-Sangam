# config.py

GEMINI_CONFIG = {
    "api_key": "AIzaSyCQe4jVtHclwO2bEj7jBcrUyBChonDRaW0",
    "other_setting": "value"
}

SNOWFLAKE_CONFIG = {
    "user": "SUBHASHREE",
    "password": "071825Subhashree",
    "account": "khqxqzz-kb71059",
    "warehouse": "COMPUTE_WH",
    "database": "TOURIST",
    "schema": "PUBLIC"
}

# def get_snowflake_connection():
#     import snowflake.connector
#     return snowflake.connector.connect(
#         user=SNOWFLAKE_CONFIG["user"],
#         password=SNOWFLAKE_CONFIG["password"],
#         account=SNOWFLAKE_CONFIG["account"],
#         warehouse=SNOWFLAKE_CONFIG["warehouse"],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
#         database=SNOWFLAKE_CONFIG["database"],
#         schema=SNOWFLAKE_CONFIG["schema"]
#     )
