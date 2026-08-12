# Entra ID (Azure AD) SSO 設定手順

**対象:** CivilPDF-DX WebUI（OIDC 認可コードフロー + PKCE）
**最終更新:** 2026-08-12

## 1. 概要

- ブラウザは `/api/v1/auth/oidc/login` にリダイレクトされ、Entra ID（または HENNGE ONE 等の OIDC IdP）で認証
- 認証後、コールバックが `id_token` を検証（issuer / audience / nonce / 署名）し、ローカルユーザーを紐付け/自動プロビジョニング
- **MFA は IdP 側（Entra Conditional Access / HENNGE）で強制**します。アプリは MFA ポリシーを緩めません
- PKCE（S256）と httpOnly state cookie により、認可コード横取りを防止

## 2. Entra ID アプリ登録

1. Azure Portal → Entra ID → アプリの登録 → 新規登録
   - リダイレクト URI: `https://<公開ドメイン>/api/v1/auth/oidc/callback`
2. 認証 → 暗黙的許可は無効のまま（認可コード + PKCE を使用）
3. 証明書とシークレット → クライアントシークレットを発行
4. トークン構成: `email` / `profile` / `openid` スコープを許可
5. （推奨）Conditional Access で MFA と準拠デバイスを要求

## 3. 環境変数

```bash
OIDC_CLIENT_ID=<アプリ登録のアプリケーションID>
OIDC_CLIENT_SECRET=<クライアントシークレット>
OIDC_DISCOVERY_URL=https://login.microsoftonline.com/<テナントID>/v2.0/.well-known/openid-configuration
OIDC_REDIRECT_URI=https://<公開ドメイン>/api/v1/auth/oidc/callback
OIDC_SCOPE=openid profile email
OIDC_AUTO_PROVISION=true
FRONTEND_ORIGIN=https://<公開ドメイン>
```

`SECRET_KEY` は OIDC の state/nonce cookie 署名にも使用するため、強力な値を設定してください。

## 4. 動作確認

1. 未ログインでログイン画面を開き「組織アカウントでログイン (SSO)」をクリック
2. Entra ID のサインイン画面へ遷移することを確認
3. 認証後、WebUI へ戻りログイン状態になることを確認
4. 監査ログに `oidc_login_success` / `oidc_user_provisioned` が記録されることを確認

## 5. トラブルシューティング

| 症状 | 対処 |
|---|---|
| 503 OIDC discovery failed | `OIDC_DISCOVERY_URL` の到達性とテナントIDを確認 |
| 502 token exchange failed | クライアントシークレット・リダイレクトURI一致を確認 |
| id_token issuer mismatch | 発行元（`/v2.0` の有無）と discovery の issuer を一致させる |
| 403 No local account | `OIDC_AUTO_PROVISION=false` の場合は事前にユーザーを作成 |
