import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { CancelSubscriptionAPI } from "api/Dashboard/subscriptionApi";
import { GetSubscriptionStatisticsAPI } from "api/Dashboard/subscriptionApi";
import { GetAllSubscriptionAPI } from "api/Dashboard/subscriptionApi";

const initialState = {
  subscriptions: [],
  statistics: {},
  loading: false,
};

export const getSubscriptions = createAsyncThunk(
  "subscription/getSubscriptions",
  async (_, { rejectWithValue }) => {
    try {
      const response = await GetAllSubscriptionAPI();
      return response.data;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);
export const getSubscriptionStatistics = createAsyncThunk(
  "subscription/getSubscriptionStatistics",
  async (_, { rejectWithValue }) => {
    try {
      const response = await GetSubscriptionStatisticsAPI();
      return response.data;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);
export const cancelSubscription = createAsyncThunk(
  "subscription/cancelSubscription",
  async (data, { rejectWithValue }) => {
    try {
      const response = await CancelSubscriptionAPI(data);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);
export const userSlice = createSlice({
  name: "subscriptions",
  initialState,
  reducers: {},
  extraReducers: (builder) =>
    builder
      .addCase(getSubscriptions.pending, (state) => {
        state.loading = true;
      })
      .addCase(getSubscriptions.fulfilled, (state, { payload }) => {
        state.subscriptions = payload.subscriptions;
        state.loading = false;
      })
      .addCase(getSubscriptions.rejected, (state) => {
        state.loading = false;
      })
      .addCase(getSubscriptionStatistics.pending, (state) => {
        state.loading = true;
      })
      .addCase(getSubscriptionStatistics.fulfilled, (state, { payload }) => {
        state.statistics = payload.statistics;
        state.loading = false;
      })
      .addCase(getSubscriptionStatistics.rejected, (state) => {
        state.loading = false;
      }),
});
export const getMeData = (state) => state.auth.meInfo;
export default userSlice.reducer;
