import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const model = new Supabase.ai.Session("gte-small");

Deno.serve(async (request) => {
  if (request.method !== "POST") {
    return Response.json({ error: "Method not allowed" }, { status: 405 });
  }

  const body = await request.json().catch(() => null);
  const text = typeof body?.text === "string" ? body.text.trim() : "";

  if (!text || text.length > 10000) {
    return Response.json(
      { error: "text must contain between 1 and 10000 characters" },
      { status: 400 },
    );
  }

  const embedding = await model.run(text, {
    mean_pool: true,
    normalize: true,
  });

  return Response.json({ embedding });
});
