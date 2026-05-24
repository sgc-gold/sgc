const TROY_OUNCE_GRAMS = 31.1034768;
const GOLDAPI_URL = "https://www.goldapi.io/api/XAU/JPY";
const FALLBACK_GOLD_URL = "https://api.gold-api.com/price/XAU";
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
      error: "GoldAPI.io did not include a usable price"
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
  const [goldResponse, usdJpyResponse] = await Promise.all([
    fetch(FALLBACK_GOLD_URL, {
      headers: { "Accept": "application/json" },
      cf: { cacheTtl: 30, cacheEverything: false }
    }),
    fetch(FALLBACK_USDJPY_URL, {
      headers: { "Accept": "application/json" },
      cf: { cacheTtl: 30, cacheEverything: false }
    })
  ]);

  const goldData = await readJsonResponse(goldResponse);
  const usdJpyData = await readJsonResponse(usdJpyResponse);

  if (!goldResponse.ok || !usdJpyResponse.ok) {
    return {
      ok: false,
      status: 502,
      error: "Fallback market data provider returned an error"
    };
  }

  const pricePerOunceUsd = finiteNumber(goldData && goldData.price);
  const usdJpyQuote = usdJpyData
    && Array.isArray(usdJpyData.quotes)
    && usdJpyData.quotes.find((quote) => quote.currencyPairCode === "USDJPY");
  const usdJpy = finiteNumber(usdJpyQuote && (usdJpyQuote.bid || usdJpyQuote.ask));

  if (!pricePerOunceUsd || !usdJpy) {
    return {
      ok: false,
      status: 502,
      error: "Fallback market data did not include a usable price"
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
      timestamp: goldData && goldData.updatedAt
        ? Math.floor(Date.parse(goldData.updatedAt) / 1000)
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
        error: "Gold market data providers returned errors",
        primaryStatus: primaryResult && primaryResult.status,
        primaryError: primaryResult && primaryResult.error,
        fallbackError: fallbackResult.error
      },
      502
    );
  } catch (error) {
    return jsonResponse(
      {
        error: "Failed to fetch gold market data",
        primaryStatus: primaryResult && primaryResult.status,
        primaryError: primaryResult && primaryResult.error
      },
      502
    );
  }
}
