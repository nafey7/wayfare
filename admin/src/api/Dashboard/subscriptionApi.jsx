import AxiosDefault from "services/AxiosDefault";

export const GetAllSubscriptionAPI = async (data) => {
  const response = await AxiosDefault({
    method: "GET",
    url: "/subscription/getSubscriptions",
    data: data,
  });
  return response;
};

export const GetSubscriptionStatisticsAPI = async (data) => {
  const response = await AxiosDefault({
    method: "GET",
    url: "/subscription/statistics",
    data: data,
  });
  return response;
};
export const CancelSubscriptionAPI = async (subscriptionId) => {
  const response = await AxiosDefault({
    method: "PATCH",
    url: `/subscription/cancel/${subscriptionId}`,
  });
  return response;
};
