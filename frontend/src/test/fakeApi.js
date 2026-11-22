import client from "../api/client";

export const realAdapter = client.defaults.adapter;

// Fake transport for page tests. Routes are keyed "METHOD /url/" and answer
// {status, data} or a function of the request config returning that.
export function fakeApi(routes) {
  const calls = [];
  client.defaults.adapter = async (config) => {
    const key = `${config.method.toUpperCase()} ${config.url}`;
    calls.push({
      key,
      params: config.params,
      data: config.data ? JSON.parse(config.data) : undefined,
    });
    const route = routes[key];
    if (!route) throw new Error(`fakeApi: no route for ${key}`);
    const { status = 200, data = {} } =
      typeof route === "function" ? route(config, calls) : route;
    const response = { data, status, statusText: "", headers: {}, config };
    if (status >= 400) {
      const error = new Error(`Request failed with status code ${status}`);
      error.config = config;
      error.response = response;
      throw error;
    }
    return response;
  };
  return calls;
}
