import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { GetAllUserAPI } from "api/Dashboard/userApi";
import { PasswordResetAPI } from "api/Dashboard/userApi";

import { GetMeInfo } from "api/Dashboard/userApi";

import { get } from "lodash";

const initialState = {
  users: [],
  meInfo: [],
  loading: false,
};

export const passwordReset = createAsyncThunk(
  "users/passwordReset",
  async (data) => {
    console.log(data, "<==data");
    try {
      const response = await PasswordResetAPI(data);
      return response.data;
    } catch (err) {
      console.log("Password reset error ======>", err);
      return err;
    }
  }
);

export const getMeInfo = createAsyncThunk(
  "auth/getMeInfo",
  async (_, { rejectWithValue }) => {
    try {
      const response = await GetMeInfo();
      return response.data;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const getUsers = createAsyncThunk(
  "users/getUsers",
  async (_, { rejectWithValue }) => {
    try {
      console.log("Api call ===>")
      const response = await GetAllUserAPI();
      return response.data;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const userSlice = createSlice({
  name: "users",
  initialState,
  reducers: {},
  extraReducers: (builder) =>
    builder
      .addCase(getUsers.pending, (state) => {
        state.loading = true;
      })
      .addCase(getUsers.fulfilled, (state, { payload }) => {
        state.users = payload.users;
        state.loading = false;
      })
      .addCase(getUsers.rejected, (state) => {
        state.loading = false;
      })
      .addCase(getMeInfo.pending, (state) => {
        state.loading = true;
      })
      .addCase(getMeInfo.fulfilled, (state, { payload }) => {
        state.meInfo = get(payload, "data", []);
        state.loading = false;
      })
      .addCase(getMeInfo.rejected, (state) => {
        state.loading = false;
      }),
});
export const getMeData = (state) => state.auth.meInfo;
export default userSlice.reducer;
