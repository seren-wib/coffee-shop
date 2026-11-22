// Turns an axios error into the line a screen shows (SDD 6.0.2, NFR-34).
export const OFFLINE_MESSAGE =
  "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.";
const FALLBACK_MESSAGE = "일시적인 오류가 발생했습니다.";

export function isOffline(error) {
  return !error?.response;
}

export function errorMessage(error) {
  if (isOffline(error)) return OFFLINE_MESSAGE;
  return error.response.data?.message || FALLBACK_MESSAGE;
}

// 400 VALIDATION_ERROR: field name -> list of Korean messages (SDD 7).
export function fieldErrors(error) {
  return error?.response?.status === 400
    ? (error.response.data?.fields ?? {})
    : {};
}
