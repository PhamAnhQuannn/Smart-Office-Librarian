export type UserRole = "user" | "admin";

export interface AuthUser {
  sub: string;           // JWT subject = user UUID
  email: string;
  role: UserRole;
  workspace_id: string;
  workspace_slug: string;
  exp: number;           // expiry in epoch seconds
}
