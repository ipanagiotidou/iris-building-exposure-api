from pydantic import BaseModel, Field, model_validator  # Using Type Hints for Data validation & Serialization


# all Pydantic models inherit from BaseModel
class BBox(BaseModel):
    # Validation happens before the service runs.

    west: float 
    south: float 
    east: float 
    north: float


    # Validation: ensures coords make sense
    @model_validator(mode= "after")    # After validators: run after the whole model (BaseModel) has been validated. After Pydantic's internal parsing.
    def validate_coords(self):         

        if self.west >= self.east : 
            raise ValueError("West must be smaller than east.")

        if self.south >= self.north: 
            raise ValueError("South must be smaller than north.")

        if not (-180 < self.west < 180):
            raise ValueError("Invalid longitude.")

        if not (-180 < self.east < 180):
            raise ValueError("Invalid longitude.")

        if not (-90 < self.north < 90):
            raise ValueError("Invalid latitude.")

        if not (-90 < self.south < 90):
            raise ValueError("Invalid latitude.")

        return self 


    # Standardisation: Gives one consistent representation of a bounding box.
    @property
    def bbox(self) -> str:            
        return f"{self.west},{self.south},{self.east},{self.north}"

    



        



        







