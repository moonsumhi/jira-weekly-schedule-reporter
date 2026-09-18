export const assetCategories = ['서버', '네트워크', '정보보호시스템', 'DBMS', 'VMware', '랙'] as const
export type AssetCategory = (typeof assetCategories)[number]
export type AssetLink = { id: string; category?: AssetCategory; name: string; ip: string; assetName: string; isDeleted: boolean }
