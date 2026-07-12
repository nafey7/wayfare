import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { GetRoles, CreateRole, UpdateRole } from "api/Dashboard/roleAPI";
import { get } from "lodash";
import { DeleteRoleAPI } from "api/Dashboard/roleAPI";
// import { StatusUpdateAPI } from "api/Dashboard/userApi";

const initialState = {
  rolesList: [],
  totalRoles: 0,
  loading: false,
};

export const getRoles = createAsyncThunk(
  "roles/getRoles",
  async (data, { rejectWithValue }) => {
    try {
      const response = await GetRoles(data);
      return response.data;
    } catch (error) {
      console.log("error ======>", error);
      return rejectWithValue(error.message);
    }
  }
);

export const createRole = createAsyncThunk(
  "roles/createRole",
  async (data, { rejectWithValue }) => {
    try {
      const response = await CreateRole(data);
      return response.data;
    } catch (error) {
      console.log("error ======>", error);
      return rejectWithValue(error.message);
    }
  }
);

export const updateRole = createAsyncThunk(
  "roles/updateRole",
  async (data, { rejectWithValue }) => {
    try {
      const response = await UpdateRole(data);
      return response.data;
    } catch (error) {
      console.log("error ======>", error);
      return rejectWithValue(error.message);
    }
  }
);

export const deleteRole = createAsyncThunk(
  "users/deleteUser",
  async (data, { rejectWithValue }) => {
    try {
      const response = await DeleteRoleAPI(data);
      return response.data;
    } catch (error) {
      console.log("error ======>", error);
      return rejectWithValue(error.message);
    }
  }
);
// export const roleStatusUpdate = createAsyncThunk(
//   "users/statusUpdate",
//   async (data, { rejectWithValue }) => {
//     try {
//       const response = await StatusUpdateAPI(data);
//       return response.data;
//     } catch (error) {
//       console.log("error ======>", error);
//       return rejectWithValue(error.message);
//     }
//   }
// );

export const roleSlice = createSlice({
  name: "roles",
  initialState,
  reducers: {},
  extraReducers: (builder) =>
    builder
      .addCase(getRoles.pending, (state) => {
        state.loading = true;
      })
      .addCase(getRoles.fulfilled, (state, { payload }) => {
        state.rolesList = get(payload, "roles", []);
        state.totalRoles = get(payload, "total", 0);
        state.loading = false;
      })
      .addCase(getRoles.rejected, (state) => {
        state.loading = false;
      }),
});

export default roleSlice.reducer;
