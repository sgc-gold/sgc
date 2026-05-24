const TROY_OUNCE_GRAMS = 31.1034768;
const GOLDAPI_URL = "https://www.goldapi.io/api/XAU/JPY";

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

export async function onRequestGet(context) {
  const token = context.env && context.env.GOLDAPI_IO_TOKEN;

  if (!token) {
    return jsonResponse(
      { error: "GOLDAPI_IO_TOKEN is not configured" },
      503
    );
  }

  let upstreamResponse;
  try {
    upstreamResponse = await fetch(GOLDAPI_URL, {
      headers: {
        "x-access-token": token,
        "Accept": "application/json"
      },
      cf: {
        cacheTtl: 30,
        cacheEverything: false
      }
    });
  } catch (error) {
    return jsonResponse(
      { error: "Failed to fetch gold market data" },
      502
    );
  }

  let upstreamData = null;
  try {
    upstreamData = await upstreamResponse.json();
  } catch (error) {
    return jsonResponse(
      { error: "Gold market data response was not valid JSON" },
      502
    );
  }

  if (!upstreamResponse.ok) {
    return jsonResponse(
      {
        error: "Gold market data provider returned an error",
        status: upstreamResponse.status
      },
      502
    );
  }

  const pricePerOunceJpy = finiteNumber(upstreamData.price);
  const providerGramPrice = finiteNumber(upstreamData.price_gram_24k);
  const pricePerGramJpy = providerGramPrice
    || (pricePerOunceJpy ? pricePerOunceJpy / TROY_OUNCE_GRAMS : null);

  if (!pricePerGramJpy) {
    return jsonResponse(
      { error: "Gold market data did not include a usable price" },
      502
    );
  }

  return jsonResponse(
    {
      pricePerGramJpy,
      pricePerOunceJpy,
      change: finiteNumber(upstreamData.ch),
      changePercent: finiteNumber(upstreamData.chp),
      timestamp: finiteNumber(upstreamData.timestamp),
      source: "GoldAPI.io"
    },
    200,
    "public, max-age=15, s-maxage=30"
  );
}
