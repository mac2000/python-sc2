from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.data import Race, Difficulty
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2.position import Point3
from sc2.unit import Unit


class DemoChallenge(BotAI):
    def __init__(self):
        super().__init__()

        self.data = dict()

        self.first_wave = False
        self.enemy_location = None
        self.scout = None
        self.scouting = False
        self.discovered = dict()
        # self.expansions = self.expansion_locations_list
        # self.enemies = self.enemy_start_locations

    async def on_step(self, iteration):
        self.draw()

        await self.ensure_are_workers_are_mining()
        await self.build_more_workers()
        await self.build_one_gas()
        await self.ensure_supply_is_good()
        await self.scout_enemy_position()
        await self.barracks()

        # marines
        for b in self.structures(UnitTypeId.BARRACKS):
            if b.has_techlab and b.is_idle and self.can_afford(UnitTypeId.MARAUDER):
                b.train(UnitTypeId.MARAUDER)
            else:
                if self.can_afford(UnitTypeId.MARINE) and b.is_idle:
                    b.train(UnitTypeId.MARINE)
                elif b.has_reactor and len(b.orders) == 1:
                    b.train(UnitTypeId.MARINE)


        # if self.scout and not self.scout.is_idle:
        #     self.on_enemy_unit_entered_vision()

        # self.units(UnitTypeId.SCV).selected

        if self.enemy_location and self.first_wave or self.units(UnitTypeId.MARINE).amount > 11:
            if not self.first_wave:
                self.first_wave = True
                await self.chat_send("sending first wave")
            for m in self.units(UnitTypeId.MARINE):
                if m.is_idle:
                    m.attack(self.enemy_location)
            for m in self.units(UnitTypeId.MARAUDER):
                if m.is_idle:
                    m.attack(self.enemy_location)
        # TODO

    async def ensure_gas_collected(self):
        for refinery in self.gas_buildings:
            if refinery.assigned_harvesters < refinery.ideal_harvesters:
                worker = self.workers.closest_to(refinery.position)
                if worker:
                    worker.gather(refinery)

    async def build_one_gas(self):
        if self.gas_buildings.amount:
            return
        if not self.can_afford(UnitTypeId.REFINERY):
            return

        vp = self.vespene_geyser.closest_to(self.townhalls.first)
        if not vp:
            return

        worker = self.workers.closest_to(vp.position)
        if not worker:
            return

        worker.build(UnitTypeId.REFINERY, vp)

    async def barracks(self):
        max_barracks = self.townhalls.amount * 3
        can_build_barrack = self.can_afford(UnitTypeId.BARRACKS)
        should_build_barrack = self.structures(UnitTypeId.BARRACKS).amount < max_barracks
        # already_building_barrack = self.already_pending(UnitTypeId.BARRACKS)
        # if can_build_barrack and should_build_barrack and not already_building_barrack:
        if can_build_barrack and should_build_barrack:
            worker = self.workers.gathering.random
            center = self.start_location.towards(self.game_info.map_center, distance=5)
            loc = await self.find_placement(UnitTypeId.BARRACKS, center, placement_step=5)
            if worker and loc:
                worker.build(UnitTypeId.BARRACKS, loc)

        for idx, b in enumerate(self.structures(UnitTypeId.BARRACKS)):
            if b.has_add_on:
                continue
            if idx % 2 == 0:
                if self.can_afford(UnitTypeId.BARRACKSTECHLAB):
                    b.build(UnitTypeId.BARRACKSTECHLAB)
            else:
                if self.can_afford(UnitTypeId.BARRACKSREACTOR):
                    b.build(UnitTypeId.BARRACKSREACTOR)

        # for b in self.structures(UnitTypeId.BARRACKS):
        #     if b.has_techlab and self.can_afford(UpgradeId.):


    async def scout_enemy_position(self):
        self.data['scouting'] = self.scouting

        if self.enemy_location:
            return

        if self.scouting:
            return

        # if not self.scout and not self.enemy_location and self.units(UnitTypeId.MARINE).amount > 0:
        #     self.scout = self.units(UnitTypeId.MARINE).idle.random
        if not self.scout:
            self.scout = self.units(UnitTypeId.SCV).random
        if not self.scout:
            return
        await self.chat_send("souting")
        for loc in self.enemy_start_locations:
            self.scouting = True
            self.scout.move(loc, queue=True)

        # for loc in self.enemy_start_locations:
        #     if loc in self.discovered:
        #         # skip already discovered locations
        #         continue
        #     almost_traveled_to_place = loc.is_closer_than(3, self.scout.position)
        #     if almost_traveled_to_place:
        #         self.discovered[loc] = True
        #         self.data[f"discovered {loc}"] = True
        #         self.scouting = False
        #         return
        #     self.data[f"scouting"] = loc
        #     self.scout.move(loc, queue=True)
        #     return

    async def ensure_supply_is_good(self):
        max_supply = 200
        supply_threshold = 5
        low_supply_left = self.supply_left < supply_threshold
        can_afford_supply_depot = self.can_afford(UnitTypeId.SUPPLYDEPOT)
        already_building_supply_depot = self.already_pending(UnitTypeId.SUPPLYDEPOT)
        already_maxed_out = self.supply_cap == max_supply

        if low_supply_left and can_afford_supply_depot and not already_building_supply_depot and not already_maxed_out:
            worker = self.workers.gathering.random
            loc = await self.find_placement(UnitTypeId.SUPPLYDEPOT, worker.position, placement_step=3)
            if worker and loc:
                worker.build(UnitTypeId.SUPPLYDEPOT, loc)

        for depot in self.structures(UnitTypeId.SUPPLYDEPOT).ready:
            if not depot.is_using_ability(AbilityId.MORPH_SUPPLYDEPOT_LOWER):
                depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

    async def build_more_workers(self):
        allowed_over_population = 3
        for base in self.townhalls:
            should_build_more = base.assigned_harvesters < base.ideal_harvesters + allowed_over_population
            if should_build_more and base.is_idle and self.can_afford(UnitTypeId.SCV):
                base.train(UnitTypeId.SCV)

    async def ensure_are_workers_are_mining(self):
        await self.distribute_workers()

    def draw(self):
        self.draw_state()
        self.draw_expansions()
        self.draw_enemy_locations()
        self.draw_townhalls()

    def draw_townhalls(self):
        for townhall in self.townhalls:
            self._client.debug_text_world(
                "\n".join(
                    [
                        f"{townhall.type_id.name}:{townhall.type_id.value}",
                        f"({townhall.position.x:.2f},{townhall.position.y:.2f})",
                        f"{townhall.build_progress:.2f}",
                        f"{townhall.assigned_harvesters}",
                        f"{townhall.ideal_harvesters}",
                    ]
                ),
                townhall.position3d,
                color=(0, 255, 0),
                size=12,
            )

    def draw_state(self):
        # Draw text in top left of screen
        # self._client.debug_text_screen(text="Hello world!", pos=Point2((0, 0)), color=None, size=16)
        # self._client.debug_text_simple(text=f"supply cap: {self.supply_cap}")
        arr = []
        for k in self.data:
            arr.append(f"{k}: {self.data[k]}")
        self._client.debug_text_simple(text="\n".join(arr))

    def draw_enemy_locations(self):
        r = Point3((255, 0, 0))
        for idx, pos in enumerate(self.enemy_start_locations):
            height = self.get_terrain_z_height(pos)
            p3 = Point3((*pos, height))
            self._client.debug_box2_out(p3, half_vertex_length=2.0, color=r)
            self._client.debug_text_world(
                f"esl {idx}",
                p3,
                color=(255, 0, 0),
                size=12,
            )

    def draw_expansions(self):
        green = Point3((0, 255, 0))
        for idx, expansion_pos in enumerate(self.expansion_locations_list):
            height = self.get_terrain_z_height(expansion_pos)
            expansion_pos3 = Point3((*expansion_pos, height))
            self._client.debug_box2_out(expansion_pos3, half_vertex_length=2.5, color=green)
            self._client.debug_text_world(
                f"exp {idx}",
                expansion_pos3,
                color=(0, 255, 0),
                size=12,
            )

    async def on_start(self):
        await self.chat_send("TODO: figure out if bot can read chat")

    async def on_enemy_unit_entered_vision(self, unit: Unit):
        if unit.type_id == UnitTypeId.COMMANDCENTER and not self.enemy_location:
            self.enemy_location = unit.position
            self.data[f"enemy discovered"] = True
            self.data[f"enemy location"] = self.enemy_location
            await self.chat_send("enemy found")
            if self.scouting and self.scout:
                self.scout.move(self.townhalls.first)
                self.scouting = False

def main():
    run_game(
        maps.get("Flat64"),
        [Bot(Race.Terran, DemoChallenge()), Computer(Race.Terran, Difficulty.Medium)],
        realtime=True
    )


if __name__ == "__main__":
    main()
