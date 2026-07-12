import AxiosDefault from "services/AxiosDefault";

export const GetAllPricingPlansAPI = async (data) => {
  const response = await AxiosDefault({
    method: "GET",
    url: "/pricing-plan/get",
    data: data,
  });
  return response;
};
