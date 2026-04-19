
from typing import Any, Dict, Optional, List, Union
from pydantic import BaseModel, Field, model_validator  # BaseModel for data validation. enables validation & serialization


class BBox(BaseModel):
    # Validation happens before the service runs.

    # bbox can be a string (with the coordinates) or None
    bbox: str | None = Field(
        default=None, 
        description="minx,miny,maxx,maxy (lon/lat, EPSG:4326)")   

    west: float | None = Field(default=None, description= "min lon", exclude=True) 
    south: float | None = Field(default=None, description= "min lat", exclude=True)
    east: float | None = Field(default=None, description= "max lon", exclude=True)
    north: float | None = Field(default=None, description= "max lat", exclude=True) 


    @model_validator(mode= "after")
    def parse_and_validate_bbox(self):

        # Case 1: bbox string provided
        
        if self.bbox is not None:
            parts = [p.strip() for p in self.bbox.split(",")]  # a list of strings  
            if len(parts) != 4:
                raise ValueError("bbox must be 'minx, miny, maxx, maxy'")
            
            try:
                west, south, east, north = (float(x) for x in parts)  # assign tuple in vars
            except ValueError:
                raise ValueError("bbox values must be numbers")
        
        # Case 2: explicit coordinates provided
        elif None not in (self.west, self.south, self.east, self.north):
            west, south, east, north = self.west, self.south, self.east, self.north

        # Case 3: Neither form provided
        else:
            raise ValueError(
                "Provide either bbox='minx,miny,maxx,maxy' or all four coordinates: "
                "west, south, east, north"
            )
        
        # Validation
        if west >= east:
            raise ValueError("west must be < east")
        if  south >=  north:
            raise ValueError("south must be < north")
        
        for lon in (west, east):
            if not (-180 <= lon <= 180):
                raise ValueError("Invalid longitude")

        for lat in (south, north):
            if not (-90 <= lat <= 90):
                raise ValueError("Invalid latitude")
        
        # Normalize internal state
        self.west = west
        self.south = south
        self.east = east
        self.north = north
    
        # Normalize bbox string consistently
        self.bbox = f"{west},{south},{east},{north}"


        return self
    
    def to_list(self) -> list[float]:
        return [self.west, self.south, self.east, self.north]  


    def to_dict(self) -> dict[str, float]:
        return {
            "west": self.west,
            "south": self.south,
            "east": self.east,
            "north": self.north,
            }
    
    def key(self) -> str:
        return f"{self.west:.6f}, {self.south: .6f}, {self.east:.6f}, {self.north:.6f}"
    


# # ANOTHER EXAMPLE

# from pydantic import BaseModel, model_validator


# class BBox(BaseModel):
#     south: float
#     north: float
#     west: float
#     east: float

#     @model_validator(mode="after")
#     def validate_bbox(self):
#         if not (-90 <= self.south <= 90):
#             raise ValueError("south must be between -90 and 90")
#         if not (-90 <= self.north <= 90):
#             raise ValueError("north must be between -90 and 90")
#         if not (-180 <= self.west <= 180):
#             raise ValueError("west must be between -180 and 180")
#         if not (-180 <= self.east <= 180):
#             raise ValueError("east must be between -180 and 180")
#         if self.south >= self.north:
#             raise ValueError("south must be less than north")
#         if self.west >= self.east:
#             raise ValueError("west must be less than east")
#         return self

#     @property
#     def dlat(self) -> float:
#         return self.north - self.south

#     @property
#     def dlon(self) -> float:
#         return self.east - self.west

#     @property
#     def mid_lat(self) -> float:
#         return (self.north + self.south) / 2

#     def to_tuple(self) -> tuple[float, float, float, float]:
#         return (self.south, self.north, self.west, self.east)

#     def to_dict(self) -> dict[str, float]:
#         return {
#             "south": self.south,
#             "north": self.north,
#             "west": self.west,
#             "east": self.east,
#         }

#     def to_filename_path(self) -> str:
#         return f"{self.south}_{self.north}_{self.west}_{self.east}"