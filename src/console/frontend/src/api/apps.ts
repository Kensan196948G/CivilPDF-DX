import { api } from './client'

export interface ReleasePackage {
  id: string
  platform: string
  format: string
  label: string
  filename: string
  version: string
  size_label: string
  sha256: string | null
  download_path: string
  available: boolean
}

export interface ChannelInfo {
  id: string
  label: string
  version: string
  release_date: string
  description: string
  user_count: number
}

export interface AppsReleasesResponse {
  stable_version: string
  packages: ReleasePackage[]
  channels: ChannelInfo[]
}

export interface DownloadUrlResponse {
  url: string | null
  message?: string
}

export async function getAppsReleases(): Promise<AppsReleasesResponse> {
  const res = await api.get<AppsReleasesResponse>('/apps/releases')
  return res.data
}

export async function getDownloadUrl(packageId: string): Promise<DownloadUrlResponse> {
  const res = await api.get<DownloadUrlResponse>(`/apps/download/${packageId}`)
  return res.data
}
