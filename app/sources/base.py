# Here we will define what every source adapter must provide.

# abc library for Abstract Base Classes
from abc import ABC, abstractmethod


class BaseBuildingAdapter(ABC):
    # declares a method that subclasses must implement.
    # Why? 
    #    --> BAG and OSM have different APIs and data structures, but both should expose a consistent method for retrieving building records. 
    #    --> This makes it easier to add another provider later.
    @abstractmethod
    def fetch_buildings(self, *args, **kwargs):
        """Retrieve building records from a source."""
        pass

