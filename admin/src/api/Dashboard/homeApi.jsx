import AxiosDefault from "services/AxiosDefault";

export const GetStatisticsAPI = async (data) => {
  const response = await AxiosDefault({
    method: "GET",
    url: "/public/statistics",
    data: data,
  });
  return response;
};
