"""
Agent definitions for the thesis simulation.
Contains the VehicleAgent class and state definitions.
"""

from enum import Enum
from mesa import Agent


class VehicleState(Enum):
    """Possible operational states for a vehicle."""
    IDLE = "IDLE"
    SERVING = "SERVING"  # In transit serving a trip
    REBALANCING = "REBALANCING"  # In transit repositioning to another zone


class VehicleAgent(Agent):
    """
    A VehicleAgent represents a vehicle (driver) in the simulation.
    It can be IDLE in a zone, SERVING a trip between zones, or REBALANCING.
    """

    def __init__(self, model, initial_zone, initial_state=VehicleState.IDLE):
        """
        Initialize the vehicle agent.
        
        Args:
            model: The ThesisSimulationModel instance.
            initial_zone: The zone ID where the vehicle starts.
            initial_state: The initial VehicleState of the vehicle.
        """
        super().__init__(model)
        self.state = initial_state
        self.current_zone = initial_zone
        
        # Transit state variables
        self.origin_zone = None
        self.destination_zone = None
        self.time_left = 0

    def assign_trip(self, origin, destination, travel_time):
        """
        Assign a trip to the vehicle, transitioning it to the SERVING state.
        
        Args:
            origin: Origin zone ID.
            destination: Destination zone ID.
            travel_time: Number of ticks required for the trip.
        """
        self.state = VehicleState.SERVING
        self.origin_zone = origin
        self.destination_zone = destination
        self.time_left = travel_time
        self.current_zone = None

    def assign_rebalance(self, origin, destination, travel_time):
        """
        Assign a rebalancing command to the vehicle, transitioning it to the REBALANCING state.
        
        Args:
            origin: Origin zone ID.
            destination: Destination zone ID.
            travel_time: Number of ticks required for the trip.
        """
        self.state = VehicleState.REBALANCING
        self.origin_zone = origin
        self.destination_zone = destination
        self.time_left = travel_time
        self.current_zone = None

    def step(self):
        """
        Advance the vehicle state.
        Decrements time_left if in transit (SERVING or REBALANCING), and transitions to IDLE upon arrival.
        """
        if self.state in (VehicleState.SERVING, VehicleState.REBALANCING):
            self.time_left -= 1
            if self.time_left <= 0:
                # Arrival at destination
                self.state = VehicleState.IDLE
                self.current_zone = self.destination_zone
                self.origin_zone = None
                self.destination_zone = None
                self.time_left = 0
