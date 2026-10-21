import { api } from 'boot/axios';

export type Team = { id: string; name: string; color: string; managerIds: string[] };
export type Building = { id: string; name: string; location: string; description: string };
export type Floor = { id: string; name: string; buildingId: string };
export type Room = Building & {
  floorId: string;
  teamIds: string[];
  managerIds: string[];
  viewerIds: string[];
  visibility: 'all' | 'members';
};
export type Person = {
  id: string;
  name: string;
  teamId: string;
  title: string;
  roomId: string | null;
  userId: string | null;
  active: boolean;
};
export type Seat = { id: string; number: string; teamId: string | null; roomId?: string };
export type Assignment = {
  id: string;
  seatId: string;
  personId: string;
  assignedAt: string;
  assignedBy: string;
};
export type ObjectKind = 'wall' | 'door' | 'desk' | 'cabinet' | 'text' | 'zone';
export type PlanObject = {
  id: string;
  kind: ObjectKind;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  seatId: string | null;
  teamId: string | null;
};
export type Plan = {
  version: number;
  width: number;
  height: number;
  objects: PlanObject[];
  seats: Seat[];
  published?: boolean;
  hasDraft?: boolean;
  createdAt?: string;
  createdBy?: string;
};
export type SpaceData = {
  revision: number;
  teams: Team[];
  buildings: Building[];
  floors: Floor[];
  rooms: Room[];
  people: Person[];
  seats: Seat[];
  assignments: Assignment[];
  plans: { roomId: string; version: number; published: boolean; hasDraft: boolean }[];
  accounts: { id: string; name: string; email: string; team: string | null }[];
  editableRoomIds: string[];
  managedTeamIds: string[];
  canManage: boolean;
  isAdmin: boolean;
};
export type EntityKind = 'teams' | 'buildings' | 'floors' | 'rooms' | 'people';
export const blankData = (): SpaceData => ({
  revision: 0,
  teams: [],
  buildings: [],
  floors: [],
  rooms: [],
  people: [],
  seats: [],
  assignments: [],
  plans: [],
  accounts: [],
  editableRoomIds: [],
  managedTeamIds: [],
  canManage: false,
  isAdmin: false,
});
export const blankPlan = (): Plan => ({
  version: 0,
  width: 1600,
  height: 1000,
  objects: [],
  seats: [],
});
export const spaceApi = {
  async snapshot() {
    return (await api.get<SpaceData>('/spaces')).data;
  },
  async save(kind: EntityKind, id: string | null, data: object, revision: number) {
    return (
      await api.request<{ id: string; revision: number }>({
        method: id ? 'PUT' : 'POST',
        url: `/spaces/${kind}${id ? `/${id}` : ''}`,
        params: { revision },
        data,
      })
    ).data;
  },
  async remove(kind: EntityKind, id: string, revision: number) {
    await api.delete(`/spaces/${kind}/${id}`, { params: { revision } });
  },
  async plan(roomId: string, draft = false) {
    return (await api.get<Plan>(`/spaces/rooms/${roomId}/plan`, { params: { draft } })).data;
  },
  async planPdf(roomId: string) {
    return api.get<Blob>(`/spaces/rooms/${roomId}/plan/pdf`, { responseType: 'blob' });
  },
  async savePlan(roomId: string, plan: Plan) {
    const { version, width, height, objects, seats } = plan;
    return (
      await api.put<{ version: number }>(`/spaces/rooms/${roomId}/plan`, {
        version,
        width,
        height,
        objects,
        seats: seats.map(({ id, number, teamId }) => ({ id, number, teamId })),
      })
    ).data;
  },
  async publish(roomId: string, version: number) {
    await api.post(`/spaces/rooms/${roomId}/plan/publish`, { version });
  },
  async removePlan(roomId: string, version: number, releaseAssignments = false, revision?: number) {
    await api.delete(`/spaces/rooms/${roomId}/plan`, {
      params: { version, release_assignments: releaseAssignments, revision },
    });
  },
  async clone(
    roomId: string,
    targetRoomId: string,
    version: number,
    source: 'draft' | 'published',
  ) {
    await api.post(`/spaces/rooms/${roomId}/plan/clone`, { targetRoomId, version, source });
  },
  async assign(seatId: string, personId: string, revision: number, teamId?: string) {
    await api.put(`/spaces/seats/${seatId}/assignment`, { personId, revision, teamId });
  },
  async unassign(seatId: string, revision: number) {
    await api.delete(`/spaces/seats/${seatId}/assignment`, { params: { revision } });
  },
};
