from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.exceptions import InvalidGeometryError, ValidationError


class RoadLink(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    source_node_id: str = Field(min_length=1)
    source_movement_id: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)
    target_lane_id: str = Field(min_length=1)
    length: float = Field(gt=0.0)
    free_flow_speed: float = Field(default=13.89, gt=0.0)

    @property
    def travel_time(self) -> float:
        return self.length / self.free_flow_speed


class IntersectionNode(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    id: str = Field(min_length=1)
    intersection: Intersection
    signal_plan: SignalPlan
    demands: tuple[Any, ...]
    pedestrian_demands: tuple[Any, ...] = ()
    controller: Any = None

    @model_validator(mode="after")
    def validate_node(self) -> "IntersectionNode":
        if self.controller is not None:
            from junction_sim.controllers.protocol import SignalController

            if not isinstance(self.controller, SignalController):
                raise ValidationError(
                    "controller must implement SignalController protocol"
                )
        return self


class IntersectionNetwork(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    id: str = Field(min_length=1)
    nodes: dict[str, IntersectionNode] = Field(min_length=1)
    links: tuple[RoadLink, ...] = ()

    @model_validator(mode="after")
    def validate_network_topology(self) -> "IntersectionNetwork":
        for node_id, node in self.nodes.items():
            if node_id != node.id:
                raise ValidationError(
                    f"node key '{node_id}' does not match node.id '{node.id}'"
                )

        link_ids: set[str] = set()
        for link in self.links:
            if link.id in link_ids:
                raise ValidationError(f"duplicate link id '{link.id}'")
            link_ids.add(link.id)

            if link.source_node_id not in self.nodes:
                raise InvalidGeometryError(
                    f"link '{link.id}' references unknown source node "
                    f"'{link.source_node_id}'"
                )
            if link.target_node_id not in self.nodes:
                raise InvalidGeometryError(
                    f"link '{link.id}' references unknown target node "
                    f"'{link.target_node_id}'"
                )
            if link.source_node_id == link.target_node_id:
                raise ValidationError(
                    f"link '{link.id}' self-loops on node '{link.source_node_id}'"
                )

            src_node = self.nodes[link.source_node_id]
            src_node.intersection.get_movement(link.source_movement_id)

            tgt_node = self.nodes[link.target_node_id]
            valid_tgt_lanes = {
                lane.id
                for app in tgt_node.intersection.approaches
                for lane in app.lanes
            }
            if link.target_lane_id not in valid_tgt_lanes:
                raise InvalidGeometryError(
                    f"link '{link.id}' target lane '{link.target_lane_id}' "
                    f"not found in node '{link.target_node_id}'"
                )

        return self

    def get_node(self, node_id: str) -> IntersectionNode:
        if node_id not in self.nodes:
            raise InvalidGeometryError(f"unknown node id '{node_id}'")
        return self.nodes[node_id]

    def get_outgoing_links(self, node_id: str) -> tuple[RoadLink, ...]:
        self.get_node(node_id)
        return tuple(lnk for lnk in self.links if lnk.source_node_id == node_id)

    def get_incoming_links(self, node_id: str) -> tuple[RoadLink, ...]:
        self.get_node(node_id)
        return tuple(lnk for lnk in self.links if lnk.target_node_id == node_id)
