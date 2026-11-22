import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import client from "../api/client";
import { realAdapter } from "./fakeApi";

afterEach(() => {
  cleanup();
  localStorage.clear();
  client.defaults.adapter = realAdapter;
});
