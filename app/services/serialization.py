import math 
import pandas as pd
import numpy as np 


# Python serialization layer that converts data from Python, pandas and NumPy into PostgreSQL JSONB
# This func solves an important problem when moving data from GeoPandas into PostgreSQL.
# Responsibility: converting PYTHON, PANDAS, and NUMPY values -->  into values that can be stored as JSON.
# SEE HERE: https://app.notion.com/p/Python-40d347b22d3b801eaf0ffbc678268dac?source=copy_link#423347b22d3b800fbda5dad76d2e0b66

# 	Convert Python, Pandas, NumPy and Shapely values into JSON-compatible Python objects.
# purpose is to produce JSON-compatible values, not simply normalize Python types.
def _normalize_python_to_json_compatible(value):

    """
    Responsibility:
    recursive normalization layer that converts Python, NumPy and Pandas values into JSON-compatible Python objects before passing them to PostgreSQL JSONB.

    I'd use this ordering:
        1. Pandas-specific values
        2. Shapely geometry
        3. NumPy-specific values
        4. Native Python values
    
    IMPORTANT:
    This function prepares values for JSON serialization.
    It does not construct JSON strings itself.

    MORE: 
    Python Native Data Types → JSON mapping
    Pandas → JSON → PostgreSQL
    convert into python data types that the JSON serialization will understand.
    NORMALIZE IN THE SENSE THAT WE *CONVERT* A PYTHON TYPE INTO A PYTHON TYPE THAT WILL BE ABLE TO BE SERIALIZED INTO JSON.
    --> Check the table: https://app.notion.com/p/Python-40d347b22d3b801eaf0ffbc678268dac?source=copy_link#424347b22d3b8085a8beeda85adcb6e1
    ORDERING MATTERS: NoneType, bool (sub-category of integers), int, float, str, dict, list, tuple

    """


    # ==========================================
    # 1. PANDAS DATA TYPES
    # ==========================================
    # pd.DataFrame, pd.Series, pd.NA, pd.NaT

    # DATAFRAMES
    # convert each row into a dictionary 
    if isinstance(value, pd.DataFrame):
        return _normalize_python_to_json_compatible(
            value.to_dict(orient="records")
        )

    # SERIES
    # convert Series into a List 
    if isinstance(value, pd.Series):
        return _normalize_python_to_json_compatible(value.tolist())


    # PANDAS MISSING VALUES:
    # Convert Pandas missing-value markers into Python None.
    # REMEMBER: Pandas often uses np.nan for missing numeric values. Your existing NumPy float handler should account for that.
    if value is pd.NA or value is pd.NaT:
        return None

    # ==========================================
    # 2. SHAPELY GEOMETRY
    # ==========================================



    # ==========================================
    # 3. NUMPY DATA TYPES
    # ==========================================

    # BOOLEAN
    # so if it is a np.bool --> I will convert into a regural Python bool value.
    if isinstance(value, np.bool_):
        return bool(value)

    # INTEGER
    # Converting NumPy integers into native Python integer.
    # np.integer instead of np.int -->  handles the different NumPy int widths.
    if isinstance(value, np.integer):
        return int(value)

    # FLOAT
    # JSON serialization understands Python floats
    # np.floating instead of np.float -->  handles the different NumPy floating-point widths.
    if isinstance(value, np.floating):  
        value = float(value)

        # Special Float Values  (NaN and Infinite)
        # checks both NaN and positive or negative infinity.
        if not math.isfinite(value):
            raise ValueError("Non-finite Numpy Float")

        # Regular Float values  
        return value

    # STRING
    # np.str_ instead of np.str -->  handles the different NumPy str widths.
    if isinstance(value, np.str_):
        return str(value)

    # ARRAY - recursively normlaize the elements 
    # A NumPy array can contain: Integers, Floats, Booleans, Strings, Nested arrays, Multiple dimensions
    # .tolist() converts NumPy arrays into native Python lists and NumPy scalar values into their corresponding Python scalar values.
    # Then your existing recursive normalizer handles the contents.
    # You don't need to write separate logic for 1D, 2D, 3D or 4D arrays.
    if isinstance(value, np.ndarray):
        return _normalize_python_to_json_compatible(value.tolist())



    # ==========================================
    # 4. NATIVE PYTHON DATA TYPES
    # ==========================================


    # NONE in python --> I should return None
    # None is a python's object representing the absence of a value akin to null in other languages. --> LACK OF DATA 
    if isinstance(value, type(None)):
        return None   

    # BOOLEAN --> return unchanged 
    # check this before integers, cause bool is a sub-category of int.
    if isinstance(value, bool):
        return value    
    
    # INTEGER --> return unchanged
    if isinstance(value, int):
        return value      

    # FLOAT --> return unchanged, with special handling for NaN/Infinity
    # NaN --> is a floating point representation of "Not a Number", used in numerical computations 
    # Python supports: float('nan'), float('inf'), float('-inf')
    # EXPLANATION FOR NONE: These are not valid standard JSON numbers. Returning None converts them to JSON null.
    # PostgreSQL can store SQL NULL in a numeric column
    if isinstance(value, float):

        # for the special values I could also raise an error instead of returning None, for e.g. raise ValueError(f"Invalid float value: {value}")
        # Special Float values : NaN and Infinity
        if math.isnan(value):  # checks if variable is equal to NaN
            return None 
        if math.isinf(value):  # checks for infinite
            return None
        
        # Normal Float Values
        return value           # unchanged for float numbers that are not NaN | Infinite   

 
    # STRING --> return unchanged. 
    if isinstance(value, str):
        return value     


    # DICT
    # FUTURE IMPROVEMENT: dictionary conversion can create duplicate keys --> SOLVE THE COLLISSION
    # DICT --> Return a Dict where keys and values are Recursively serialized. 
    # dict in python --> should turn into an object in JSON 
    # An object in JSON is exactly like a dictionary 
    # Keys should be String (in JSON), and values should be [...] depending on what they are in the beginning. 
    # EXAMPLE: PYTHON = { 1: "John", "age": 25, "active": True }   --> JSON = { "1": "John", "age": 25, "active": true }
    # You see that all keys turned into strings ! and most values remained unchanged, but it really depends on what python data type they are!  
    # TWO THINGS HAPPENING: 
    # 1. str(key) converts dictionary keys into strings because JSON object keys must be strings.
    # 2. _normalize_python(val) recursively normalizes every value.
    if isinstance(value, dict):
        return {
            str(key): _normalize_python_to_json_compatible(val)
            for key, val in value.items()
        }

    # LIST | TUPLE --> convert to List and recursively serialize 
    # list or tuple in python --> should turn into a list in JSON, where each item of the list should be serialized according to what it is.  
    if isinstance(value, (list, tuple)):
        return [_normalize_python_to_json_compatible(item) for item in value]



    # UNSUPPORTED TYPE
    # Fail explicitly

    raise TypeError(f"Unsupported Python type: {type(value).__name__}") 

