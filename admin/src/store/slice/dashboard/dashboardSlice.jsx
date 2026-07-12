import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { GetStatisticsAPI } from "api/Dashboard/homeApi";

const initialState = {
  statistics: {},
  loading: false,
};

export const getStatistics = createAsyncThunk(
  "dashboard/getStatistics",
  async (_, { rejectWithValue }) => {
    try {
      const response = await GetStatisticsAPI();
      return response.data;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const dashboardSlice = createSlice({
  name: "dashboard",
  initialState,
  reducers: {},
  extraReducers: (builder) =>
    builder

      .addCase(getStatistics.pending, (state) => {
        state.loading = true;
      })
      .addCase(getStatistics.fulfilled, (state, { payload }) => {
        state.statistics = payload.statistics;
        state.loading = false;
      })
      .addCase(getStatistics.rejected, (state) => {
        state.loading = false;
      }),
});
export default dashboardSlice.reducer;
