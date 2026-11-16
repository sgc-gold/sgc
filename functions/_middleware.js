import {createInternalMiddleware} from '../lib/internal-sso.mjs';
import {verifyLegacyAccess} from '../lib/legacy-access.mjs';
export const onRequest=createInternalMiddleware({verifyLegacy:verifyLegacyAccess});
