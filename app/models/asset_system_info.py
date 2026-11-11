"""Editable server specifications, independent of operating-system command formats."""
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Text = Annotated[str, Field(max_length=256)]
Count = Annotated[int, Field(ge=1, le=1048576)]
Capacity = Annotated[float, Field(ge=0, le=1073741824, allow_inf_nan=False)]
ByteSize = Annotated[int, Field(ge=0, le=9007199254740991)]


class InfoModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True,
                             alias_generator=to_camel, populate_by_name=True)


class CpuInfo(InfoModel):
    manufacturer: Text = ''
    model: Text = ''
    architecture: Text = ''
    sockets: Count | None = None
    core_count: Count | None = None
    logical_cpus: Count | None = None
    threads_per_core: Count | None = None
    frequency: Text = ''
    virtualization: Text = ''
    cache: Text = ''
    cores_per_socket: Count | None = None
    frequency_mhz: Capacity | None = None
    thread_list: Annotated[str, Field(max_length=4000)] = ''
    numa_nodes: Count | None = None


class MemoryInfo(InfoModel):
    total_gb: Capacity | None = None
    total_slots: Annotated[int, Field(ge=0, le=65536)] | None = None
    max_capacity_gb: Capacity | None = None
    ecc: Text = ''
    installed_slots: Annotated[int, Field(ge=0, le=65536)] | None = None


class MemoryModule(InfoModel):
    slot: Text = ''
    status: Literal['', '장착', '미장착', '확인 필요'] = ''
    capacity_gb: Capacity | None = None
    size_bytes: ByteSize | None = None
    type: Text = ''
    speed: Text = ''
    manufacturer: Text = ''
    model: Text = ''
    serial: Text = ''
    part_number: Text = ''
    specification: Text = ''
    form_factor: Text = ''


class DiskInfo(InfoModel):
    name: Text = ''
    type: Literal['', '디스크', '파티션', '논리 볼륨', '광학 장치', '기타'] = ''
    capacity: Text = ''
    filesystem: Text = ''
    mount_point: Text = ''
    parent: Text = ''
    model: Text = ''
    serial: Text = ''
    manufacturer: Text = ''
    kernel_name: Text = ''
    partition_label: Text = ''
    filesystem_label: Text = ''
    size_bytes: ByteSize | None = None
    uuid: Text = ''
    revision: Text = ''


class PartitionInfo(InfoModel):
    mount_point: Text = ''
    source: Text = ''
    size_bytes: ByteSize | None = None
    used_bytes: ByteSize | None = None
    available_bytes: ByteSize | None = None
    used_percent: Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)] | None = None
    filesystem: Text = ''


class HardwareInfo(InfoModel):
    board_manufacturer: Text = ''
    board_model: Text = ''
    board_serial: Text = ''
    chassis: Text = ''
    bios_manufacturer: Text = ''
    bios_version: Text = ''
    bios_date: date | None = None
    board_version: Text = ''
    board_features: Annotated[str, Field(max_length=4000)] = ''
    bios_revision: Text = ''
    bios_features: Annotated[str, Field(max_length=4000)] = ''


class NetworkInterface(InfoModel):
    name: Text = ''
    type: Literal['', '물리', '본딩', '브리지', 'VLAN', '가상', '루프백', '기타'] = ''
    state: Literal['', '활성', '비활성', '확인 필요'] = ''
    mtu: Annotated[int, Field(ge=1, le=1048576)] | None = None
    ipv4: Annotated[str, Field(max_length=1024)] = ''
    ipv6: Annotated[str, Field(max_length=1024)] = ''
    mac: Text = ''
    permanent_mac: Text = ''
    parent: Text = ''
    speed: Text = ''
    netmask: Text = ''
    gateway: Text = ''
    bonding_options: Annotated[str, Field(max_length=4000)] = ''


class GpuInfo(InfoModel):
    manufacturer: Text = ''
    product_name: Text = ''
    core_codename: Text = ''


class SystemInformation(InfoModel):
    cpu: CpuInfo = Field(default_factory=CpuInfo)
    memory: MemoryInfo = Field(default_factory=MemoryInfo)
    memory_modules: list[MemoryModule] = Field(default_factory=list, max_length=128)
    disks: list[DiskInfo] = Field(default_factory=list, max_length=256)
    partitions: list[PartitionInfo] = Field(default_factory=list, max_length=512)
    hardware: HardwareInfo = Field(default_factory=HardwareInfo)
    network_interfaces: list[NetworkInterface] = Field(default_factory=list, max_length=128)
    gpus: list[GpuInfo] = Field(default_factory=list, max_length=128)
    notes: Annotated[str, Field(max_length=4000)] = ''
