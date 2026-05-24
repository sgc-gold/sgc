const TROY_OUNCE_GRAMS = 31.1034768;
const GOLDAPI_URL = "https://www.goldapi.io/api/XPT/JPY";
const FALLBACK_METAL_URL = "https://api.gold-api.com/price/XPT";
const FALLBACK_USDJPY_URL = "https://www.gaitameonline.com/rateaj/getrate";

function jsonResponse(body, status = 200, cacheControl = "no-store") {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": cacheControl
    }
  });
}

function finiteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

async function readJsonResponse(response) {
  try {
    return await response.json();
  } catch (error) {
    return null;
  }
}

async function fetchGoldApiIo(token) {
  const response = await fetch(GOLDAPI_URL, {
    headers: {
      "x-access-token": token,
      "Accept": "application/json"
    },
    cf: {
      cacheTtl: 30,
      cacheEverything: false
    }
  });
  const data = await readJsonResponse(response);

  if (!response.ok) {
    return {
      ok: false,
      status: response.status,
      error: data && (data.error || data.message)
    };
  }

  const pricePerOunceJpy = finiteNumber(data && data.price);
  const providerGramPrice = finiteNumber(data && data.price_gram_24k);
  const pricePerGramJpy = providerGramPrice
    || (pricePerOunceJpy ? pricePerOunceJpy / TROY_OUNCE_GRAMS : null);

  if (!pricePerGramJpy) {
    return {
      ok: false,
      status: 502,
      error: "GoldAPI.io did not include a usable platinum price"
    };
  }

  return {
    ok: true,
    body: {
      pricePerGramJpy,
      pricePerOunceJpy,
      change: finiteNumber(data.ch),
      changePercent: finiteNumber(data.chp),
      timestamp: finiteNumber(data.timestamp),
      source: "GoldAPI.io"
    }
  };
}

async function fetchFallbackPrice() {
  const [metalResponse, usdJpyResponse] = await Promise.all([
    fetch(FALLBACK_METAL_URL, {
      headers: { "Accept": "application/json" },
      cf: { cacheTtl: 30, cacheEverything: false }
    }),
    fetch(FALLBACK_USDJPY_URL, {
      headers: { "Accept": "application/json" },
      cf: { cacheTtl: 30, cacheEverything: false }
    })
  ]);

  const metalData = await readJsonResponse(metalResponse);
  const usdJpyData = await readJsonResponse(usdJpyResponse);

  if (!metalResponse.ok || !usdJpyResponse.ok) {
    return {
      ok: false,
      status: 502,
      error: "Fallback market data provider returned an error"
    };
  }

  const pricePerOunceUsd = finiteNumber(metalData && metalData.price);
  const usdJpyQuote = usdJpyData
    && Array.isArray(usdJpyData.quotes)
    && usdJpyData.quotes.find((quote) => quote.currencyPairCode === "USDJPY");
  const usdJpy = finiteNumber(usdJpyQuote && (usdJpyQuote.bid || usdJpyQuote.ask));

  if (!pricePerOunceUsd || !usdJpy) {
    return {
      ok: false,
      status: 502,
      error: "Fallback market data did not include a usable platinum price"
    };
  }

  const pricePerOunceJpy = pricePerOunceUsd * usdJpy;

  return {
    ok: true,
    body: {
      pricePerGramJpy: pricePerOunceJpy / TROY_OUNCE_GRAMS,
      pricePerOunceJpy,
      change: null,
      changePercent: null,
      timestamp: metalData && metalData.updatedAt
        ? Math.floor(Date.parse(metalData.updatedAt) / 1000)
        : null,
      source: "Gold API + USD/JPY"
    }
  };
}

export async function onRequestGet(context) {
  const token = context.env && context.env.GOLDAPI_IO_TOKEN;

  let primaryResult = null;
  try {
    if (token) {
      primaryResult = await fetchGoldApiIo(token);
      if (primaryResult.ok) {
        return jsonResponse(primaryResult.body, 200, "public, max-age=15, s-maxage=30");
      }
    }
  } catch (error) {
    primaryResult = { ok: false, status: 502, error: "Failed to fetch GoldAPI.io data" };
  }

  try {
    const fallbackResult = await fetchFallbackPrice();
    if (fallbackResult.ok) {
      return jsonResponse(fallbackResult.body, 200, "public, max-age=15, s-maxage=30");
    }

    return jsonResponse(
      {
        error: "Platinum market data providers returned errors",
        primaryStatus: primaryResult && primaryResult.status,
        primaryError: primaryResult && primaryResult.error,
        fallbackError: fallbackResult.error
      },
      502
    );
  } catch (error) {
    return jsonResponse(
      {
        error: "Failed to fetch platinum market data",
        primaryStatus: primaryResult && primaryResult.status,
        primaryError: primaryResult && primaryResult.error
      },
      502
    );
  }
}
