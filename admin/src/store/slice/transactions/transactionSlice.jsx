import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { GetTransactionsAPI } from "api/Dashboard/transactionAPI";

import { get } from "lodash";

const initialState = {
  list: [],
  totalTransactions: 0,
  loading: false,
};

export const getTransactions = createAsyncThunk(
  "transactions/getTransactions",
  async (data) => {
    try {
      const response = await GetTransactionsAPI(data);
      return response.data;
    } catch (err) {
      console.log("Get Transactions error ======>", err);
      return err;
    }
  }
);

export const transactionSlice = createSlice({
  name: "transactions",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(getTransactions.pending, (state) => {
        state.loading = true;
      })
      .addCase(getTransactions.fulfilled, (state, action) => {
        state.list = get(action.payload, "success", false)
          ? action.payload.transactions
          : [];
        state.totalTransactions = get(action.payload, "total", 0);
        state.loading = false;
      })
      .addCase(getTransactions.rejected, (state) => {
        state.loading = false;
      });
  },
});

export default transactionSlice.reducer;
