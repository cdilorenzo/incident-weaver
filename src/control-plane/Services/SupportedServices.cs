namespace ControlPlane.Services;

public static class SupportedServices
{
    public const string CheckoutApi = "checkout-api";

    public static bool IsSupported(string service) =>
        string.Equals(service, CheckoutApi, StringComparison.Ordinal);
}
