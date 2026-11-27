# Here we will define what every source adapter must provide.

# abc library for Abstract Base Classes
from abc import ABC, abstractmethod


# Definition of a Common Adapter Interface: We define here what every source adapter should provide. 
# abstract base classes (ABC) that define common container behaviors
class BaseBuildingAdapter(ABC):

    # declares a method that subclasses must implement.
    # Why? 
    #    --> BAG and OSM have different APIs and data structures, but both should expose a consistent method for retrieving/fetching building records. 
    #    --> This makes it easier to add another provider later.


    # it can take an arbitrary number of arguments, and keyword arguments
    @abstractmethod
    def fetch_buildings(self, *args, **kwargs):
        """Retrieve building records from a source."""
        pass
