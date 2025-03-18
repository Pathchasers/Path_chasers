import base64
import oracledb
from datetime import datetime
from decimal import Decimal

def serialize_data(value):
    """Handles serialization of datetime, BLOB, CLOB, and other data types"""
    
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")  # Convert datetime to string
    
    elif isinstance(value, Decimal):
        return float(value)  # Convert Decimal to float
    
    elif isinstance(value, bytes):  # Handle BLOB or RAW data
        return base64.b64encode(value).decode("utf-8")  # Convert binary to Base64 string
    
    elif isinstance(value, oracledb.LOB):  # Handle CLOB and BLOB
        lob_value = value.read()
        if isinstance(lob_value, bytes):  # If it's BLOB (binary data)
            return base64.b64encode(lob_value).decode("utf-8")  # Convert to Base64 string
        return lob_value  # If it's CLOB (text data)
    
    elif value is None:
        return None  # JSON uses `null` instead of `None`
    
    return value  # Return other types as-is