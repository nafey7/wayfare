import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { GetAllPricingPlansAPI } from "api/Dashboard/pricingPlanApi";

const initialState = {
  pricingPlans: [],
  loading: false,
};

export const getPricingPlans = createAsyncThunk(
  "pricingPlan/getPricingPlans",
  async (_, { rejectWithValue }) => {
    try {
      const response = await GetAllPricingPlansAPI();
      return response.data;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const pricingPlanSlice = createSlice({
  name: "pricingPlans",
  initialState,
  reducers: {},
  extraReducers: (builder) =>
    builder
      .addCase(getPricingPlans.pending, (state) => {
        state.loading = true;
      })
      .addCase(getPricingPlans.fulfilled, (state, { payload }) => {
        state.pricingPlans = payload.pricingPlans;
        state.loading = false;
      })
      .addCase(getPricingPlans.rejected, (state) => {
        state.loading = false;
      }),
});
export default pricingPlanSlice.reducer;
