from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

#--------------------------------------
# 饰品类型枚举
class Accessory(Enum):
    CAP = "cap"
    RING = "ring"
    NECKLACE = "necklace"
    KNAPSACK = "knapsack"
    BROOCH = "brooch"
    LEG_RING = "leg_ring"
    EARRING = "earring"
    SHOES = "shoes"
    SOCKS = "socks"

#物品的耐久
@dataclass
class Durability:
    now: int
    max: int
    def degrade(self, amount: int = 1) -> bool:
        """降低耐久，返回是否物品破损"""
        self.now -= amount
        if self.now <= 0:
            self.now = 0
            return True  # 物品破损
        return False  # 物品未破损

# 基础物品类
@dataclass
class Item:
    name: str
    description: str = ""
    durability: Optional[Durability] = None



# 饰品类
@dataclass
class Ornament(Item):
    accessory_type: Accessory

#---------------------------------------

#物品栏类，包含多个物品
@dataclass
class ItemSlot:
    items: list[Item]
    max_capacity: int

    def add_item(self, item: Item) -> bool:
        """添加物品到物品栏"""
        if len(self.items) < self.max_capacity:
            self.items.append(item)
            return True
        return False  # 物品栏已满

    def remove_item(self, item: Item) -> bool:
        """从物品栏移除物品"""
        if item in self.items:
            self.items.remove(item)
            return True
        return False

    def list_items(self) -> list[Item]:
        """列出物品栏中的所有物品"""
        return self.items

# 饰品栏类，包含多个饰品
@dataclass
class OrnamentSlot:
    cap: Optional[Ornament] = None
    ring: List[Optional[Ornament]] = field(default_factory=lambda: [None, None])
    necklace: Optional[Ornament] = None
    knapsack: Optional[Ornament] = None
    brooch: Optional[Ornament] = None
    leg_ring: List[Optional[Ornament]] = field(default_factory=lambda: [None, None])
    earring: List[Optional[Ornament]] = field(default_factory=lambda: [None, None])
    shoes: List[Optional[Ornament]] = field(default_factory=lambda: [None, None])
    socks: List[Optional[Ornament]] = field(default_factory=lambda: [None, None])
    
    def add_ornament(self, ornament: Ornament, location:int) -> Optional[Ornament]:
        """添加饰品到对应槽位"""
        if ornament.accessory_type == Accessory.CAP:
            old = self.cap
            self.cap = ornament
            return old
        elif ornament.accessory_type == Accessory.RING:
            if 0 <= location < len(self.ring):
                old = self.ring[location]
                self.ring[location] = ornament
                return old
        elif ornament.accessory_type == Accessory.NECKLACE:
            old = self.necklace
            self.necklace = ornament
            return old
        elif ornament.accessory_type == Accessory.KNAPSACK:
            old = self.knapsack
            self.knapsack = ornament
            return old
        elif ornament.accessory_type == Accessory.BROOCH:
            old = self.brooch
            self.brooch = ornament
            return old
        elif ornament.accessory_type == Accessory.LEG_RING:
            if 0 <= location < len(self.leg_ring):
                old = self.leg_ring[location]
                self.leg_ring[location] = ornament
                return old
        elif ornament.accessory_type == Accessory.EARRING:
            if 0 <= location < len(self.earring):
                old = self.earring[location]
                self.earring[location] = ornament
                return old
        elif ornament.accessory_type == Accessory.SHOES:
            if 0 <= location < len(self.shoes):
                old = self.shoes[location]
                self.shoes[location] = ornament
                return old
        elif ornament.accessory_type == Accessory.SOCKS:
            if 0 <= location < len(self.socks):
                old = self.socks[location]
                self.socks[location] = ornament
                return old
        return None  # 添加失败，位置无效或类型不匹配

    
    def remove_ornament(self, ornament:Ornament) -> Optional[Ornament]:
        """从饰品栏移除饰品"""
        if ornament.accessory_type == Accessory.CAP and self.cap == ornament:
            self.cap = None
            return ornament
        elif ornament.accessory_type == Accessory.RING:
            for i in range(len(self.ring)):
                if self.ring[i] == ornament:
                    self.ring[i] = None
                    return ornament
        elif ornament.accessory_type == Accessory.NECKLACE and self.necklace == ornament:
            self.necklace = None
            return ornament
        elif ornament.accessory_type == Accessory.KNAPSACK and self.knapsack == ornament:
            self.knapsack = None
            return ornament
        elif ornament.accessory_type == Accessory.BROOCH and self.brooch == ornament:
            self.brooch = None
            return ornament
        elif ornament.accessory_type == Accessory.LEG_RING:
            for i in range(len(self.leg_ring)):
                if self.leg_ring[i] == ornament:
                    self.leg_ring[i] = None
                    return ornament
        elif ornament.accessory_type == Accessory.EARRING:
            for i in range(len(self.earring)):
                if self.earring[i] == ornament:
                    self.earring[i] = None
                    return ornament
        elif ornament.accessory_type == Accessory.SHOES:
            for i in range(len(self.shoes)):
                if self.shoes[i] == ornament:
                    self.shoes[i] = None
                    return ornament
        elif ornament.accessory_type == Accessory.SOCKS:
            for i in range(len(self.socks)):
                if self.socks[i] == ornament:
                    self.socks[i] = None
                    return ornament
        return None  # 移除失败，未找到该饰品

    def list_ornaments(self) -> Dict[str, List[Optional[Ornament]]]:
        """列出饰品栏中的所有饰品"""
        return {
            "cap": [self.cap],
            "ring": self.ring,
            "necklace": [self.necklace],
            "knapsack": [self.knapsack],
            "brooch": [self.brooch],
            "leg_ring": self.leg_ring,
            "earring": self.earring,
            "shoes": self.shoes,
            "socks": self.socks,
        }
    
#--------------------------------------
# 角色类，包含物品栏和饰品栏
@dataclass
class Character:
    user_id: int
    name: str
    item_slot: ItemSlot = field(default_factory=lambda: ItemSlot(items=[], max_capacity=20))
    ornament_slot: OrnamentSlot = field(default_factory=OrnamentSlot)

    def add_item(self, item: Item) -> bool:
        """添加物品到物品栏"""
        return self.item_slot.add_item(item)

    def remove_item(self, item: Item) -> bool:
        """从物品栏移除物品"""
        return self.item_slot.remove_item(item)

    def list_items(self) -> list[Item]:
        """列出物品栏中的所有物品"""
        return self.item_slot.list_items()

    def add_ornament(self, ornament: Ornament, location:int) -> Optional[Ornament]:
        """添加饰品到饰品栏"""
        return self.ornament_slot.add_ornament(ornament, location)

    def remove_ornament(self, ornament: Ornament) -> Optional[Ornament]:
        """从饰品栏移除饰品"""
        return self.ornament_slot.remove_ornament(ornament)

    def list_ornaments(self) -> Dict[str, List[Optional[Ornament]]]:
        """列出饰品栏中的所有饰品"""
        return self.ornament_slot.list_ornaments()