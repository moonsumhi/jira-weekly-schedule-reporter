export const assetCategories = ['서버', '네트워크', '스토리지', '소프트웨어', '정보보호시스템', 'DBMS', 'VMware', '랙'] as const
export const editableAssetCategories = assetCategories.filter(category => category !== '랙')
export type AssetCategory = (typeof assetCategories)[number]
export type AssetLink = { id: string; category?: AssetCategory; name: string; ip: string; assetName: string; isDeleted: boolean }
