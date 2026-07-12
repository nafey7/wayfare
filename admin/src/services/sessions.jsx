export const savePublicSession = (data) => {
  localStorage.setItem("brandId", data.brandId);
};

export const getPublicSession = () => {
  return {
    brandId: localStorage.getItem("brandId"),
  };
};

export const clearPublicSession = () => {
  localStorage.removeItem("brandId");
};
